from __future__ import annotations

import math
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from jinja2 import Template
from PIL import Image

from slidebridge.core.metadata import summary
from slidebridge.core.registry import open_slide
from slidebridge.overlays.heatmap import attach_scores, load_scores
from slidebridge.overlays.patch_table import PatchTable
from slidebridge.overlays.patches import load_patch_table
from slidebridge.utils.image import ensure_rgb


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

    slide = open_slide(slide_path, reader=reader)
    info = summary(slide)
    width = int(info["width"])
    height = int(info["height"])
    max_dzi_level = int(math.ceil(math.log2(max(width, height)))) if max(width, height) > 1 else 0

    patch_table = PatchTable(records=[])
    if heatmap_path is not None and patches_path is None:
        raise ValueError("--heatmap requires --patches so scores can be aligned to coordinates")
    if patches_path:
        patch_table = load_patch_table(patches_path, default_patch_size=default_patch_size)
        if heatmap_path is not None:
            patch_table = attach_scores(patch_table, load_scores(heatmap_path))
        if score_normalization != "none":
            patch_table = patch_table.normalize_scores(score_normalization)  # type: ignore[arg-type]
        patch_table = patch_table.validate(width, height, mode="clip")

    patch_summary = patch_table.summary()
    patch_warnings = list(patch_summary.get("warnings", []))
    if len(patch_table) > max_overlay_patches:
        patch_warnings.append(
            f"overlay_truncated:{max_overlay_patches}:{len(patch_table)}"
        )
    patch_warning = "; ".join(patch_warnings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        del app
        try:
            yield
        finally:
            slide.close()

    app = FastAPI(title="SlideBridge Viewer", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        template_path = Path(__file__).parent / "templates" / "viewer.html"
        template = Template(template_path.read_text(encoding="utf-8"))
        return HTMLResponse(
            template.render(
                filename=info["filename"],
                width=width,
                height=height,
                reader=info["reader"],
                mpp_x=info["mpp_x"],
                mpp_y=info["mpp_y"],
                objective_power=info["objective_power"],
                vendor=info["vendor"],
                warnings=info["warnings"],
                patch_count=len(patch_table),
                patch_warning=patch_warning,
                heatmap_opacity=max(0.0, min(float(heatmap_opacity), 1.0)),
            )
        )

    @app.get("/api/info")
    def api_info() -> dict:
        return info

    @app.get("/api/patches")
    def api_patches() -> dict:
        returned_records = patch_table.records[:max_overlay_patches]
        scores = [record.score for record in patch_table.records if record.score is not None]
        warnings = list(patch_summary.get("warnings", []))
        if len(patch_table) > max_overlay_patches:
            warnings.append(
                f"Returning first {max_overlay_patches} of {len(patch_table)} patches for viewer responsiveness."
            )
        return {
            "count": len(patch_table),
            "returned": len(returned_records),
            "has_scores": bool(scores),
            "score_min": min(scores) if scores else None,
            "score_max": max(scores) if scores else None,
            "warnings": warnings,
            "patches": [record.to_dict() for record in returned_records],
        }

    @app.get("/dzi.dzi")
    def dzi() -> Response:
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" Format="jpeg" Overlap="0" TileSize="{tile_size}">
  <Size Width="{width}" Height="{height}"/>
</Image>
"""
        return Response(content=xml, media_type="application/xml")

    @app.get("/dzi_files/{level}/{col}_{row}.jpeg")
    def tile(level: int, col: int, row: int) -> Response:
        if level < 0:
            raise HTTPException(status_code=404, detail="Tile level must be non-negative")
        if col < 0 or row < 0:
            raise HTTPException(status_code=404, detail="Tile column and row must be non-negative")
        if level > max_dzi_level:
            raise HTTPException(status_code=404, detail="Tile level is outside the Deep Zoom pyramid")

        downsample = 2 ** (max_dzi_level - level)
        level_width = int(math.ceil(width / downsample))
        level_height = int(math.ceil(height / downsample))
        x_l = col * tile_size
        y_l = row * tile_size
        if x_l >= level_width or y_l >= level_height:
            raise HTTPException(status_code=404, detail="Tile column or row is outside this level")

        tile_w_l = min(tile_size, level_width - x_l)
        tile_h_l = min(tile_size, level_height - y_l)
        x0 = int(x_l * downsample)
        y0 = int(y_l * downsample)
        if x0 >= width or y0 >= height:
            raise HTTPException(status_code=404, detail="Tile origin is outside slide bounds")

        region_w0 = max(1, min(int(math.ceil(tile_w_l * downsample)), width - x0))
        region_h0 = max(1, min(int(math.ceil(tile_h_l * downsample)), height - y0))

        best_level = slide.get_best_level_for_downsample(float(downsample))
        best_downsample = float(slide.level_downsamples[best_level])
        read_w = max(1, int(math.ceil(region_w0 / best_downsample)))
        read_h = max(1, int(math.ceil(region_h0 / best_downsample)))

        image = slide.read_region(x0, y0, read_w, read_h, level=best_level)
        image = ensure_rgb(image)
        if image.size != (tile_w_l, tile_h_l):
            image = image.resize((tile_w_l, tile_h_l), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=jpeg_quality)
        return Response(
            content=buffer.getvalue(),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    return app
