from __future__ import annotations

import json
import math
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import RLock
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from PIL import Image

from slidebridge.annotations.io import load_annotation_table
from slidebridge.annotations.table import AnnotationTable
from slidebridge.core.metadata import summary
from slidebridge.core.registry import open_slide
from slidebridge.overlays.heatmap import attach_scores, load_scores
from slidebridge.overlays.patch_table import PatchTable
from slidebridge.overlays.patches import load_patch_table
from slidebridge.utils.image import ensure_rgb
from slidebridge.utils.paths import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_WSI_EXTENSIONS


VIEWABLE_EXTENSIONS = SUPPORTED_WSI_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS
NO_STORE_HEADERS = {"Cache-Control": "no-store"}
CACHEABLE_TILE_HEADERS = {"Cache-Control": "public, max-age=3600"}


@dataclass(frozen=True)
class SlideEntry:
    id: int
    path: Path
    filename: str
    relative_path: str
    size_bytes: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": str(self.path),
            "filename": self.filename,
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
        }


@dataclass
class SlideSession:
    entry: SlideEntry
    slide: Any
    info: dict[str, Any]
    width: int
    height: int
    max_dzi_level: int


@dataclass
class OverlayContext:
    table: PatchTable
    summary: dict[str, Any]
    warning: str


@dataclass
class AnnotationContext:
    table: AnnotationTable
    summary: dict[str, Any]
    warning: str


def create_app(
    slide_path: str | Path,
    patches_path: str | Path | None = None,
    reader: str | None = None,
    tile_size: int = 256,
    jpeg_quality: int = 85,
    heatmap_path: str | Path | None = None,
    default_patch_size: int = 256,
    heatmap_opacity: float = 0.45,
    score_normalization: str = "minmax",
    max_overlay_patches: int = 50_000,
    annotations_path: str | Path | None = None,
    annotation_format: str | None = None,
    annotation_opacity: float = 0.35,
    max_annotations: int = 10_000,
    annotation_labels: list[str] | None = None,
    recursive: bool = False,
    max_slides: int = 500,
    viewer_context: str = "local",
    viewer_remote_user: str | None = None,
    viewer_remote_host: str | None = None,
    viewer_remote_ssh_port: int | None = None,
    viewer_source: str | None = None,
) -> FastAPI:
    tile_size = int(tile_size)
    jpeg_quality = int(jpeg_quality)
    if tile_size <= 0:
        raise ValueError("tile_size must be a positive integer")
    if jpeg_quality < 1 or jpeg_quality > 100:
        raise ValueError("jpeg_quality must be between 1 and 100")
    if score_normalization not in {"minmax", "percentile", "none"}:
        raise ValueError("score_normalization must be one of: minmax, percentile, none")
    max_overlay_patches = max(0, int(max_overlay_patches))
    max_annotations = max(0, int(max_annotations))
    max_slides = max(1, int(max_slides))

    source = Path(slide_path)
    entries = _collect_slide_entries(source, recursive=recursive, max_slides=max_slides)
    if not entries:
        raise FileNotFoundError(f"No viewable slide files found: {source}")
    library_mode = source.is_dir()
    viewer_context = str(viewer_context or "local").lower()
    if viewer_context not in {"local", "remote"}:
        raise ValueError("viewer_context must be local or remote")
    viewer_source = viewer_source or str(source)
    library_warning = ""
    if library_mode and len(entries) >= max_slides:
        library_warning = f"Showing first {max_slides} viewable files. Increase --max-slides if needed."

    if heatmap_path is not None and patches_path is None:
        raise ValueError("--heatmap requires --patches so scores can be aligned to coordinates")

    tile_cache_key = secrets.token_hex(8)
    lock = RLock()
    sessions: dict[int, SlideSession] = {}
    patch_cache: dict[int, OverlayContext] = {}
    annotation_cache: dict[int, AnnotationContext] = {}

    def get_entry(slide_id: int) -> SlideEntry:
        if slide_id < 0 or slide_id >= len(entries):
            raise HTTPException(status_code=404, detail="Slide id is outside the loaded directory")
        return entries[slide_id]

    def get_session(slide_id: int = 0) -> SlideSession:
        with lock:
            if slide_id in sessions:
                return sessions[slide_id]
            entry = get_entry(slide_id)
            slide = open_slide(entry.path, reader=reader)
            info = summary(slide)
            info["slide_id"] = entry.id
            info["relative_path"] = entry.relative_path
            info["library_root"] = str(source) if library_mode else str(entry.path.parent)
            width = int(info["width"])
            height = int(info["height"])
            max_dzi_level = int(math.ceil(math.log2(max(width, height)))) if max(width, height) > 1 else 0
            session = SlideSession(entry, slide, info, width, height, max_dzi_level)
            sessions[slide_id] = session
            return session

    def get_patch_context(slide_id: int = 0) -> OverlayContext:
        if slide_id in patch_cache:
            return patch_cache[slide_id]
        session = get_session(slide_id)
        patch_table = PatchTable(records=[])
        if patches_path:
            patch_table = load_patch_table(patches_path, default_patch_size=default_patch_size)
            if heatmap_path is not None:
                patch_table = attach_scores(patch_table, load_scores(heatmap_path))
            if score_normalization != "none":
                patch_table = patch_table.normalize_scores(score_normalization)  # type: ignore[arg-type]
            patch_table = patch_table.validate(session.width, session.height, mode="clip")
        patch_summary = patch_table.summary()
        patch_warnings = list(patch_summary.get("warnings", []))
        if len(patch_table) > max_overlay_patches:
            patch_warnings.append(f"overlay_truncated:{max_overlay_patches}:{len(patch_table)}")
        context = OverlayContext(patch_table, patch_summary, "; ".join(patch_warnings))
        patch_cache[slide_id] = context
        return context

    def get_annotation_context(slide_id: int = 0) -> AnnotationContext:
        if slide_id in annotation_cache:
            return annotation_cache[slide_id]
        session = get_session(slide_id)
        annotation_table = AnnotationTable(records=[])
        if annotations_path is not None:
            annotation_table = load_annotation_table(annotations_path, format=annotation_format).compute_bboxes().normalize_colors()
            if annotation_labels:
                annotation_table = annotation_table.filter_labels(annotation_labels)
            annotation_table = annotation_table.validate(session.width, session.height, mode="warn")
        annotation_summary = annotation_table.summary()
        annotation_warnings = list(annotation_summary.get("warnings", []))
        if len(annotation_table) > max_annotations:
            annotation_warnings.append(
                f"Returning first {max_annotations} of {len(annotation_table)} annotations for viewer responsiveness."
            )
        context = AnnotationContext(annotation_table, annotation_summary, "; ".join(annotation_warnings))
        annotation_cache[slide_id] = context
        return context

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        del app
        try:
            yield
        finally:
            with lock:
                for session in sessions.values():
                    session.slide.close()
                sessions.clear()

    app = FastAPI(title="SlideBridge Viewer", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        session = get_session(0)
        patch_context = get_patch_context(0)
        annotation_context = get_annotation_context(0)
        template_path = Path(__file__).parent / "templates" / "viewer.html"
        template = Template(template_path.read_text(encoding="utf-8"))
        return HTMLResponse(
            template.render(
                filename=session.info["filename"],
                width=session.width,
                height=session.height,
                reader=session.info["reader"],
                mpp_x=session.info["mpp_x"],
                mpp_y=session.info["mpp_y"],
                objective_power=session.info["objective_power"],
                vendor=session.info["vendor"],
                warnings=session.info["warnings"],
                patch_count=len(patch_context.table),
                patch_warning=patch_context.warning,
                heatmap_opacity=max(0.0, min(float(heatmap_opacity), 1.0)),
                annotation_count=len(annotation_context.table),
                annotation_warning=annotation_context.warning,
                annotation_opacity=max(0.0, min(float(annotation_opacity), 1.0)),
                library_mode=library_mode,
                library_root=str(source),
                library_recursive=recursive,
                library_warning=library_warning,
                slide_count=len(entries),
                slides_json=json.dumps([entry.to_dict() for entry in entries], ensure_ascii=False),
                tile_cache_key=tile_cache_key,
                viewer_context=viewer_context,
                viewer_remote_user=viewer_remote_user,
                viewer_remote_host=viewer_remote_host,
                viewer_remote_ssh_port=viewer_remote_ssh_port,
                viewer_source=viewer_source,
            ),
            headers=NO_STORE_HEADERS,
        )

    @app.get("/api/slides")
    def api_slides() -> JSONResponse:
        return _json_response({
            "count": len(entries),
            "root": str(source),
            "library_mode": library_mode,
            "recursive": recursive,
            "warnings": [library_warning] if library_warning else [],
            "slides": [entry.to_dict() for entry in entries],
        })

    @app.get("/api/info")
    def api_info(slide_id: int = Query(0, ge=0)) -> JSONResponse:
        return _json_response(get_session(slide_id).info)

    @app.get("/api/patches")
    def api_patches(slide_id: int = Query(0, ge=0)) -> JSONResponse:
        context = get_patch_context(slide_id)
        patch_table = context.table
        returned_records = patch_table.records[:max_overlay_patches]
        scores = [record.score for record in patch_table.records if record.score is not None]
        warnings = list(context.summary.get("warnings", []))
        if library_mode and patches_path:
            warnings.append("The same patch file is applied to the selected slide in directory viewer mode.")
        if len(patch_table) > max_overlay_patches:
            warnings.append(
                f"Returning first {max_overlay_patches} of {len(patch_table)} patches for viewer responsiveness."
            )
        return _json_response({
            "count": len(patch_table),
            "returned": len(returned_records),
            "has_scores": bool(scores),
            "score_min": min(scores) if scores else None,
            "score_max": max(scores) if scores else None,
            "warnings": warnings,
            "patches": [record.to_dict() for record in returned_records],
        })

    @app.get("/api/annotations")
    def api_annotations(slide_id: int = Query(0, ge=0)) -> JSONResponse:
        context = get_annotation_context(slide_id)
        annotation_table = context.table
        returned_records = annotation_table.records[:max_annotations]
        warnings = list(context.summary.get("warnings", []))
        if library_mode and annotations_path:
            warnings.append("The same annotation file is applied to the selected slide in directory viewer mode.")
        if len(annotation_table) > max_annotations:
            warnings.append(
                f"Returning first {max_annotations} of {len(annotation_table)} annotations for viewer responsiveness."
            )
        return _json_response({
            "count": len(annotation_table),
            "returned": len(returned_records),
            "coordinate_space": annotation_table.coordinate_space,
            "labels": annotation_table.labels(),
            "type_counts": context.summary.get("type_counts", {}),
            "warnings": warnings,
            "annotations": [record.to_dict() for record in returned_records],
        })

    @app.get("/dzi.dzi")
    def dzi(slide_id: int = Query(0, ge=0)) -> Response:
        return _dzi_response(get_session(slide_id), tile_size)

    @app.get("/slides/{slide_id}/dzi.dzi")
    def slide_dzi(slide_id: int) -> Response:
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        return _dzi_response(get_session(slide_id), tile_size)

    @app.get("/slides/{slide_id}/{cache_key}/dzi.dzi")
    def slide_dzi_with_cache_key(slide_id: int, cache_key: str) -> Response:
        _validate_cache_key(cache_key, tile_cache_key)
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        return _dzi_response(get_session(slide_id), tile_size)

    @app.get("/dzi_files/{level}/{col}_{row}.jpeg")
    def tile(level: int, col: int, row: int, slide_id: int = Query(0, ge=0)) -> Response:
        return _tile_response(get_session(slide_id), level, col, row, tile_size, jpeg_quality, cacheable=False)

    @app.get("/slides/{slide_id}/dzi_files/{level}/{col}_{row}.jpeg")
    def slide_tile(slide_id: int, level: int, col: int, row: int) -> Response:
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        return _tile_response(get_session(slide_id), level, col, row, tile_size, jpeg_quality, cacheable=False)

    @app.get("/slides/{slide_id}/{cache_key}/dzi_files/{level}/{col}_{row}.jpeg")
    def slide_tile_with_cache_key(slide_id: int, cache_key: str, level: int, col: int, row: int) -> Response:
        _validate_cache_key(cache_key, tile_cache_key)
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        return _tile_response(get_session(slide_id), level, col, row, tile_size, jpeg_quality, cacheable=True)

    return app


def _collect_slide_entries(source: Path, recursive: bool, max_slides: int) -> list[SlideEntry]:
    if source.is_file():
        return [_slide_entry(0, source, source.parent)]
    if not source.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {source}")

    pattern = "**/*" if recursive else "*"
    paths: list[Path] = []
    for item in source.glob(pattern):
        if item.is_file() and item.suffix.lower() in VIEWABLE_EXTENSIONS:
            paths.append(item)
            if len(paths) >= max_slides:
                break
    return [_slide_entry(index, path, source) for index, path in enumerate(sorted(paths)[:max_slides])]


def _slide_entry(index: int, path: Path, root: Path) -> SlideEntry:
    try:
        relative = str(path.relative_to(root))
    except ValueError:
        relative = path.name
    try:
        size = path.stat().st_size
    except OSError:
        size = None
    return SlideEntry(index, path, path.name, relative, size)


def _dzi_response(session: SlideSession, tile_size: int) -> Response:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" Format="jpeg" Overlap="0" TileSize="{tile_size}">
  <Size Width="{session.width}" Height="{session.height}"/>
</Image>
"""
    return Response(content=xml, media_type="application/xml", headers=NO_STORE_HEADERS)


def _json_response(payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(content=payload, headers=NO_STORE_HEADERS)


def _tile_response(
    session: SlideSession,
    level: int,
    col: int,
    row: int,
    tile_size: int,
    jpeg_quality: int,
    cacheable: bool,
) -> Response:
    if level < 0:
        raise HTTPException(status_code=404, detail="Tile level must be non-negative")
    if col < 0 or row < 0:
        raise HTTPException(status_code=404, detail="Tile column and row must be non-negative")
    if level > session.max_dzi_level:
        raise HTTPException(status_code=404, detail="Tile level is outside the Deep Zoom pyramid")

    downsample = 2 ** (session.max_dzi_level - level)
    level_width = int(math.ceil(session.width / downsample))
    level_height = int(math.ceil(session.height / downsample))
    x_l = col * tile_size
    y_l = row * tile_size
    if x_l >= level_width or y_l >= level_height:
        raise HTTPException(status_code=404, detail="Tile column or row is outside this level")

    tile_w_l = min(tile_size, level_width - x_l)
    tile_h_l = min(tile_size, level_height - y_l)
    x0 = int(x_l * downsample)
    y0 = int(y_l * downsample)
    if x0 >= session.width or y0 >= session.height:
        raise HTTPException(status_code=404, detail="Tile origin is outside slide bounds")

    region_w0 = max(1, min(int(math.ceil(tile_w_l * downsample)), session.width - x0))
    region_h0 = max(1, min(int(math.ceil(tile_h_l * downsample)), session.height - y0))

    best_level = session.slide.get_best_level_for_downsample(float(downsample))
    best_downsample = float(session.slide.level_downsamples[best_level])
    read_w = max(1, int(math.ceil(region_w0 / best_downsample)))
    read_h = max(1, int(math.ceil(region_h0 / best_downsample)))

    image = session.slide.read_region(x0, y0, read_w, read_h, level=best_level)
    image = ensure_rgb(image)
    if image.size != (tile_w_l, tile_h_l):
        image = image.resize((tile_w_l, tile_h_l), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=jpeg_quality)
    return Response(
        content=buffer.getvalue(),
        media_type="image/jpeg",
        headers=CACHEABLE_TILE_HEADERS if cacheable else NO_STORE_HEADERS,
    )


def _validate_cache_key(cache_key: str, expected: str) -> None:
    if cache_key != expected:
        raise HTTPException(status_code=404, detail="Tile cache key is no longer valid")
