from __future__ import annotations

import json
import math
import re
import secrets
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import RLock, Semaphore
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
from slidebridge.overlays.raster_heatmap import RasterHeatmap, is_raster_heatmap_path, load_raster_heatmap
from slidebridge.render.view import render_view_to_image
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


@dataclass
class RasterHeatmapContext:
    heatmap: RasterHeatmap | None
    summary: dict[str, Any]
    warning: str


@dataclass(frozen=True)
class RasterHeatmapLayerSpec:
    id: str
    name: str
    path: Path


class TileCache:
    def __init__(self, max_entries: int, max_bytes: int | None = None) -> None:
        self.max_entries = max(0, int(max_entries))
        self.max_bytes = max(0, int(max_bytes or 0))
        self._items: OrderedDict[tuple[Any, ...], bytes] = OrderedDict()
        self._lock = RLock()
        self._bytes = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    @property
    def enabled(self) -> bool:
        return self.max_entries > 0

    def get(self, key: tuple[Any, ...]) -> bytes | None:
        if not self.enabled:
            return None
        with self._lock:
            if key not in self._items:
                self.misses += 1
                return None
            self.hits += 1
            value = self._items.pop(key)
            self._items[key] = value
            return value

    def set(self, key: tuple[Any, ...], value: bytes) -> None:
        if not self.enabled:
            return
        with self._lock:
            if key in self._items:
                old = self._items.pop(key)
                self._bytes -= len(old)
            self._items[key] = value
            self._bytes += len(value)
            while self._over_limit():
                _, evicted = self._items.popitem(last=False)
                self._bytes -= len(evicted)
                self.evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._bytes = 0

    def _over_limit(self) -> bool:
        if not self._items:
            return False
        if self.max_entries > 0 and len(self._items) > self.max_entries:
            return True
        if self.max_bytes > 0 and self._bytes > self.max_bytes:
            return True
        return False

    def stats(self, tile_workers: int) -> dict[str, int | bool]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "max_entries": self.max_entries,
                "max_bytes": self.max_bytes,
                "max_mb": round(self.max_bytes / (1024 * 1024), 3) if self.max_bytes else 0,
                "entries": len(self._items),
                "bytes": self._bytes,
                "mb": round(self._bytes / (1024 * 1024), 3),
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "tile_workers": int(tile_workers),
            }


class TileMetrics:
    def __init__(self, max_samples: int = 2000) -> None:
        self.max_samples = max(1, int(max_samples))
        self._lock = RLock()
        self._samples: OrderedDict[int, dict[str, float]] = OrderedDict()
        self._next_id = 0
        self.generated_tiles = 0
        self.cache_served_tiles = 0

    def record_generated(self, timings: dict[str, float]) -> None:
        with self._lock:
            self.generated_tiles += 1
            self._samples[self._next_id] = timings
            self._next_id += 1
            while len(self._samples) > self.max_samples:
                self._samples.popitem(last=False)

    def record_cache_hit(self) -> None:
        with self._lock:
            self.cache_served_tiles += 1

    def stats(self) -> dict[str, Any]:
        with self._lock:
            samples = list(self._samples.values())
            return {
                "generated_tiles": self.generated_tiles,
                "cache_served_tiles": self.cache_served_tiles,
                "sample_count": len(samples),
                "read_region_ms": _metric_summary(samples, "read_region_ms"),
                "resize_ms": _metric_summary(samples, "resize_ms"),
                "jpeg_encode_ms": _metric_summary(samples, "jpeg_encode_ms"),
                "total_tile_ms": _metric_summary(samples, "total_tile_ms"),
            }


def create_app(
    slide_path: str | Path,
    patches_path: str | Path | None = None,
    reader: str | None = None,
    tile_size: int = 256,
    jpeg_quality: int = 85,
    heatmap_path: str | Path | None = None,
    raster_heatmap_path: str | Path | None = None,
    raster_heatmap_layers: list[dict[str, Any]] | None = None,
    default_patch_size: int = 256,
    heatmap_opacity: float = 0.45,
    score_normalization: str = "minmax",
    max_overlay_patches: int = 50_000,
    annotations_path: str | Path | None = None,
    annotation_format: str | None = None,
    annotation_opacity: float = 0.35,
    max_annotations: int = 10_000,
    annotation_labels: list[str] | None = None,
    max_raster_heatmap_size: int = 4096,
    raster_heatmap_threshold: float | None = None,
    raster_heatmap_invert: bool = False,
    raster_heatmap_colormap: str = "auto",
    recursive: bool = False,
    max_slides: int = 500,
    viewer_context: str = "local",
    viewer_remote_user: str | None = None,
    viewer_remote_host: str | None = None,
    viewer_remote_ssh_port: int | None = None,
    viewer_source: str | None = None,
    tile_cache_size: int = 512,
    tile_cache_mb: int = 256,
    tile_workers: int = 4,
) -> FastAPI:
    tile_size = int(tile_size)
    jpeg_quality = int(jpeg_quality)
    tile_cache_size = int(tile_cache_size)
    tile_cache_mb = int(tile_cache_mb)
    tile_workers = int(tile_workers)
    if tile_size <= 0:
        raise ValueError("tile_size must be a positive integer")
    if jpeg_quality < 1 or jpeg_quality > 100:
        raise ValueError("jpeg_quality must be between 1 and 100")
    if tile_cache_size < 0:
        raise ValueError("tile_cache_size must be zero or a positive integer")
    if tile_cache_mb < 0:
        raise ValueError("tile_cache_mb must be zero or a positive integer")
    if tile_workers < 1 or tile_workers > 64:
        raise ValueError("tile_workers must be between 1 and 64")
    if score_normalization not in {"minmax", "percentile", "none"}:
        raise ValueError("score_normalization must be one of: minmax, percentile, none")
    if raster_heatmap_threshold is not None and not (0.0 <= float(raster_heatmap_threshold) <= 1.0):
        raise ValueError("raster_heatmap_threshold must be between 0 and 1")
    raster_heatmap_colormap = str(raster_heatmap_colormap or "auto").lower()
    if raster_heatmap_colormap not in {"auto", "score", "grayscale", "none"}:
        raise ValueError("raster_heatmap_colormap must be one of: auto, score, grayscale, none")
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

    if heatmap_path is not None and is_raster_heatmap_path(heatmap_path):
        if raster_heatmap_path is not None:
            raise ValueError("Use either --heatmap PNG/JPG or --raster-heatmap, not both.")
        raster_heatmap_path = heatmap_path
        heatmap_path = None

    if heatmap_path is not None and patches_path is None:
        raise ValueError("--heatmap requires --patches so scores can be aligned to coordinates")

    raster_heatmap_specs = _normalize_raster_heatmap_specs(raster_heatmap_path, raster_heatmap_layers)
    first_raster_heatmap_path = raster_heatmap_specs[0].path if raster_heatmap_specs else None

    snapshot_options = {
        "patches": str(patches_path) if patches_path is not None else None,
        "heatmap": str(heatmap_path) if heatmap_path is not None else None,
        "raster_heatmap": str(first_raster_heatmap_path) if first_raster_heatmap_path is not None else None,
        "raster_heatmap_layers": [
            {"name": spec.name, "path": str(spec.path), "id": spec.id}
            for spec in raster_heatmap_specs
        ],
        "annotations": str(annotations_path) if annotations_path is not None else None,
        "annotation_format": annotation_format,
        "default_patch_size": default_patch_size,
        "score_normalization": score_normalization,
        "max_raster_heatmap_size": max_raster_heatmap_size,
        "raster_heatmap_threshold": raster_heatmap_threshold,
        "raster_heatmap_invert": bool(raster_heatmap_invert),
        "raster_heatmap_colormap": raster_heatmap_colormap,
        "viewer_context": viewer_context,
    }

    tile_cache_key = secrets.token_hex(8)
    lock = RLock()
    sessions: dict[int, SlideSession] = {}
    patch_cache: dict[int, OverlayContext] = {}
    annotation_cache: dict[int, AnnotationContext] = {}
    raster_heatmap_cache: dict[tuple[int, str], RasterHeatmapContext] = {}
    tile_cache = TileCache(tile_cache_size, max_bytes=tile_cache_mb * 1024 * 1024)
    tile_metrics = TileMetrics()
    tile_semaphore = Semaphore(tile_workers)

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

    def get_raster_heatmap_context(slide_id: int = 0, layer_id: str | None = None) -> RasterHeatmapContext:
        session = get_session(slide_id)
        spec = _find_raster_heatmap_spec(raster_heatmap_specs, layer_id)
        if spec is None:
            context = RasterHeatmapContext(None, {"available": False, "warnings": []}, "")
            return context
        cache_key = (slide_id, spec.id)
        if cache_key in raster_heatmap_cache:
            return raster_heatmap_cache[cache_key]
        heatmap = load_raster_heatmap(
            spec.path,
            max_size=max_raster_heatmap_size,
            threshold=raster_heatmap_threshold,
            invert=raster_heatmap_invert,
            colormap=raster_heatmap_colormap,
        )
        summary_payload = heatmap.summary(slide_width=session.width, slide_height=session.height)
        summary_payload["id"] = spec.id
        summary_payload["name"] = spec.name
        warnings = list(summary_payload.get("warnings", []))
        if library_mode:
            warnings.append("The same raster heatmap is applied to the selected slide in directory viewer mode.")
        summary_payload["warnings"] = warnings
        context = RasterHeatmapContext(heatmap, summary_payload, "; ".join(warnings))
        raster_heatmap_cache[cache_key] = context
        return context

    def get_raster_heatmap_payload(slide_id: int = 0) -> dict[str, Any]:
        if not raster_heatmap_specs:
            return {"available": False, "count": 0, "layers": [], "warnings": []}
        layers = []
        warnings: list[str] = []
        for spec in raster_heatmap_specs:
            context = get_raster_heatmap_context(slide_id, spec.id)
            payload = dict(context.summary)
            if context.heatmap is not None:
                payload["url"] = f"/slides/{int(slide_id)}/{tile_cache_key}/raster_heatmaps/{spec.id}.png"
                layers.append(payload)
            warnings.extend(payload.get("warnings", []))
        return {
            "available": bool(layers),
            "count": len(layers),
            "layers": layers,
            "warnings": warnings,
        }

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
                tile_cache.clear()

    app = FastAPI(title="SlideBridge Viewer", lifespan=lifespan)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        session = get_session(0)
        patch_context = get_patch_context(0)
        annotation_context = get_annotation_context(0)
        raster_heatmap_payload = get_raster_heatmap_payload(0)
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
                raster_heatmap_available=bool(raster_heatmap_payload.get("available")),
                raster_heatmap_warning=_raster_heatmap_global_warning_text(raster_heatmap_payload.get("warnings", [])),
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
                snapshot_options=json.dumps(snapshot_options, ensure_ascii=False),
                tile_cache_stats=json.dumps(tile_cache.stats(tile_workers), ensure_ascii=False),
                tile_performance_stats=json.dumps(tile_metrics.stats(), ensure_ascii=False),
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

    @app.get("/api/raster-heatmap")
    def api_raster_heatmap(slide_id: int = Query(0, ge=0)) -> JSONResponse:
        payload = get_raster_heatmap_payload(slide_id)
        if payload["layers"]:
            first = dict(payload["layers"][0])
            first["url"] = f"/slides/{int(slide_id)}/{tile_cache_key}/raster_heatmap.png"
            first["layers"] = payload["layers"]
            first["count"] = payload["count"]
            first["warnings"] = payload["warnings"]
            payload = first
        return _json_response(payload)

    @app.get("/api/raster-heatmaps")
    def api_raster_heatmaps(slide_id: int = Query(0, ge=0)) -> JSONResponse:
        return _json_response(get_raster_heatmap_payload(slide_id))

    @app.get("/api/cache-stats")
    def api_cache_stats() -> JSONResponse:
        return _json_response(tile_cache.stats(tile_workers))

    @app.get("/api/performance")
    def api_performance() -> JSONResponse:
        return _json_response({
            "cache": tile_cache.stats(tile_workers),
            "tiles": tile_metrics.stats(),
        })

    @app.get("/api/render-view")
    def api_render_view(
        slide_id: int = Query(0, ge=0),
        center_x: float = Query(...),
        center_y: float = Query(...),
        window_width: int = Query(..., ge=1),
        window_height: int = Query(..., ge=1),
        out_width: int = Query(1600, ge=1, le=4096),
        out_height: int | None = Query(None, ge=1, le=4096),
        include_patches: bool = Query(True),
        include_annotations: bool = Query(True),
        include_raster_heatmap: bool = Query(True),
        score_threshold: float = Query(0.0, ge=0.0, le=1.0),
        top_k: int = Query(0, ge=0),
        annotation_labels: str | None = Query(None),
        opacity: float | None = Query(None, ge=0.0, le=1.0),
        annotation_opacity_query: float | None = Query(None, alias="annotation_opacity", ge=0.0, le=1.0),
    ) -> Response:
        session = get_session(slide_id)
        patch_table = PatchTable(records=[])
        if include_patches:
            patch_table = _filter_patch_table_for_snapshot(get_patch_context(slide_id).table, score_threshold, top_k)
        annotation_table = AnnotationTable(records=[])
        if include_annotations:
            annotation_table = get_annotation_context(slide_id).table
            labels = _split_query_labels(annotation_labels)
            if labels:
                annotation_table = annotation_table.filter_labels(labels)
        raster_path = first_raster_heatmap_path if include_raster_heatmap else None
        image, _ = render_view_to_image(
            session.slide,
            patch_table=patch_table,
            annotation_table=annotation_table,
            center_x=center_x,
            center_y=center_y,
            window_width=window_width,
            window_height=window_height,
            out_width=out_width,
            out_height=out_height,
            opacity=heatmap_opacity if opacity is None else opacity,
            annotation_opacity=annotation_opacity if annotation_opacity_query is None else annotation_opacity_query,
            raster_heatmap_path=raster_path,
            raster_heatmap_opacity=heatmap_opacity if opacity is None else opacity,
            max_raster_heatmap_size=max_raster_heatmap_size,
            raster_heatmap_threshold=raster_heatmap_threshold,
            raster_heatmap_invert=raster_heatmap_invert,
            raster_heatmap_colormap=raster_heatmap_colormap,
        )
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        filename = f"slidebridge_view_s{int(slide_id)}_x{int(round(center_x))}_y{int(round(center_y))}.png"
        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={
                **NO_STORE_HEADERS,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

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
        return _tile_response(
            get_session(slide_id),
            level,
            col,
            row,
            tile_size,
            jpeg_quality,
            cacheable=False,
            tile_cache=tile_cache,
            tile_metrics=tile_metrics,
            tile_semaphore=tile_semaphore,
            tile_cache_key=tile_cache_key,
        )

    @app.get("/slides/{slide_id}/dzi_files/{level}/{col}_{row}.jpeg")
    def slide_tile(slide_id: int, level: int, col: int, row: int) -> Response:
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        return _tile_response(
            get_session(slide_id),
            level,
            col,
            row,
            tile_size,
            jpeg_quality,
            cacheable=False,
            tile_cache=tile_cache,
            tile_metrics=tile_metrics,
            tile_semaphore=tile_semaphore,
            tile_cache_key=tile_cache_key,
        )

    @app.get("/slides/{slide_id}/{cache_key}/dzi_files/{level}/{col}_{row}.jpeg")
    def slide_tile_with_cache_key(slide_id: int, cache_key: str, level: int, col: int, row: int) -> Response:
        _validate_cache_key(cache_key, tile_cache_key)
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        return _tile_response(
            get_session(slide_id),
            level,
            col,
            row,
            tile_size,
            jpeg_quality,
            cacheable=True,
            tile_cache=tile_cache,
            tile_metrics=tile_metrics,
            tile_semaphore=tile_semaphore,
            tile_cache_key=tile_cache_key,
        )

    @app.get("/slides/{slide_id}/{cache_key}/raster_heatmap.png")
    def slide_raster_heatmap(slide_id: int, cache_key: str) -> Response:
        _validate_cache_key(cache_key, tile_cache_key)
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        context = get_raster_heatmap_context(slide_id)
        if context.heatmap is None:
            raise HTTPException(status_code=404, detail="No raster heatmap is loaded")
        return Response(
            content=context.heatmap.to_png_bytes(),
            media_type="image/png",
            headers=CACHEABLE_TILE_HEADERS,
        )

    @app.get("/slides/{slide_id}/{cache_key}/raster_heatmaps/{layer_id}.png")
    def slide_raster_heatmap_layer(slide_id: int, cache_key: str, layer_id: str) -> Response:
        _validate_cache_key(cache_key, tile_cache_key)
        if slide_id < 0:
            raise HTTPException(status_code=404, detail="Slide id must be non-negative")
        context = get_raster_heatmap_context(slide_id, layer_id)
        if context.heatmap is None:
            raise HTTPException(status_code=404, detail="No raster heatmap layer is loaded")
        return Response(
            content=context.heatmap.to_png_bytes(),
            media_type="image/png",
            headers=CACHEABLE_TILE_HEADERS,
        )

    return app


def _normalize_raster_heatmap_specs(
    raster_heatmap_path: str | Path | None,
    raster_heatmap_layers: list[dict[str, Any]] | None,
) -> list[RasterHeatmapLayerSpec]:
    raw: list[tuple[str | None, str | Path]] = []
    if raster_heatmap_path is not None:
        raw.append((None, raster_heatmap_path))
    for layer in raster_heatmap_layers or []:
        if not isinstance(layer, dict):
            raise ValueError("Raster heatmap layers must be dictionaries with path and optional name.")
        path = layer.get("path")
        if not path:
            raise ValueError("Raster heatmap layer is missing a path.")
        raw.append((str(layer.get("name") or "").strip() or None, path))

    specs: list[RasterHeatmapLayerSpec] = []
    for index, (name, path_value) in enumerate(raw):
        path = Path(path_value)
        if not is_raster_heatmap_path(path):
            raise ValueError("Raster heatmap layers must point to PNG, JPG, or JPEG files.")
        label = name or path.stem or f"heatmap {index + 1}"
        specs.append(RasterHeatmapLayerSpec(_raster_heatmap_layer_id(index, label, path), label, path))
    return specs


def _raster_heatmap_layer_id(index: int, name: str, path: Path) -> str:
    base = str(name or path.stem or f"heatmap-{index + 1}").strip().lower()
    base = re.sub(r"[^a-z0-9_-]+", "-", base).strip("-")
    if not base:
        base = f"heatmap-{index + 1}"
    return f"{int(index)}-{base}"


def _find_raster_heatmap_spec(
    specs: list[RasterHeatmapLayerSpec],
    layer_id: str | None,
) -> RasterHeatmapLayerSpec | None:
    if not specs:
        return None
    if layer_id is None:
        return specs[0]
    for spec in specs:
        if spec.id == layer_id:
            return spec
    raise HTTPException(status_code=404, detail="Raster heatmap layer was not found")


def _raster_heatmap_global_warning_text(warnings: list[str] | Any) -> str:
    if not isinstance(warnings, list):
        return ""
    global_warnings: list[str] = []
    for warning in warnings:
        text = str(warning or "")
        if _is_layer_raster_heatmap_warning(text):
            continue
        if text and text not in global_warnings:
            global_warnings.append(text)
    return "; ".join(global_warnings)


def _is_layer_raster_heatmap_warning(warning: str) -> bool:
    return (
        warning.startswith("raster_heatmap_resized:")
        or warning == "raster_heatmap_aspect_ratio_mismatch"
        or warning == "raster_heatmap_no_finite_values"
        or warning == "raster_heatmap_constant_values"
        or warning == "raster_heatmap_threshold_hides_all_pixels"
    )


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


def _split_query_labels(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _filter_patch_table_for_snapshot(table: PatchTable, score_threshold: float, top_k: int) -> PatchTable:
    records = list(table.records)
    threshold = max(0.0, min(1.0, float(score_threshold or 0.0)))
    if threshold > 0:
        records = [
            record
            for record in records
            if record.score is not None and float(record.score) >= threshold
        ]
    if top_k > 0:
        if any(record.score is not None for record in records):
            records = sorted(records, key=lambda record: float(record.score or 0.0), reverse=True)
        records = records[: int(top_k)]
    return PatchTable(
        records=records,
        source=table.source,
        coordinate_space=table.coordinate_space,
        default_patch_size=table.default_patch_size,
        metadata=dict(table.metadata),
    )


def _tile_response(
    session: SlideSession,
    level: int,
    col: int,
    row: int,
    tile_size: int,
    jpeg_quality: int,
    cacheable: bool,
    tile_cache: TileCache,
    tile_metrics: TileMetrics,
    tile_semaphore: Semaphore,
    tile_cache_key: str,
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

    cache_key = (
        tile_cache_key,
        int(session.entry.id),
        int(level),
        int(col),
        int(row),
        int(tile_size),
        int(jpeg_quality),
    )
    if cacheable:
        cached = tile_cache.get(cache_key)
        if cached is not None:
            tile_metrics.record_cache_hit()
            return Response(content=cached, media_type="image/jpeg", headers=CACHEABLE_TILE_HEADERS)

    total_start = time.perf_counter()
    read_region_ms = 0.0
    resize_ms = 0.0
    jpeg_encode_ms = 0.0
    with tile_semaphore:
        read_start = time.perf_counter()
        image = session.slide.read_region(x0, y0, read_w, read_h, level=best_level)
        read_region_ms = _elapsed_ms(read_start)
        image = ensure_rgb(image)
        if image.size != (tile_w_l, tile_h_l):
            resize_start = time.perf_counter()
            image = image.resize((tile_w_l, tile_h_l), Image.Resampling.LANCZOS)
            resize_ms = _elapsed_ms(resize_start)

        buffer = BytesIO()
        jpeg_start = time.perf_counter()
        image.save(buffer, format="JPEG", quality=jpeg_quality)
        jpeg_encode_ms = _elapsed_ms(jpeg_start)
        content = buffer.getvalue()
    tile_metrics.record_generated({
        "read_region_ms": read_region_ms,
        "resize_ms": resize_ms,
        "jpeg_encode_ms": jpeg_encode_ms,
        "total_tile_ms": _elapsed_ms(total_start),
    })
    if cacheable:
        tile_cache.set(cache_key, content)
    return Response(
        content=content,
        media_type="image/jpeg",
        headers=CACHEABLE_TILE_HEADERS if cacheable else NO_STORE_HEADERS,
    )


def _validate_cache_key(cache_key: str, expected: str) -> None:
    if cache_key != expected:
        raise HTTPException(status_code=404, detail="Tile cache key is no longer valid")


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 3)


def _metric_summary(samples: list[dict[str, float]], key: str) -> dict[str, float | int | None]:
    values = sorted(float(sample.get(key, 0.0)) for sample in samples)
    if not values:
        return {"avg": None, "p95": None, "count": 0}
    return {
        "avg": round(sum(values) / len(values), 3),
        "p95": round(values[min(len(values) - 1, int(math.ceil(len(values) * 0.95)) - 1)], 3),
        "count": len(values),
    }
