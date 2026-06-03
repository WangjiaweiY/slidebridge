from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from slidebridge.annotations.render import draw_annotations
from slidebridge.annotations.table import AnnotationRecord, AnnotationTable
from slidebridge.core.protocol import Slide
from slidebridge.overlays.patch_table import PatchTable
from slidebridge.overlays.raster_heatmap import RasterHeatmap, load_raster_heatmap
from slidebridge.render.overlay import _format_from_path, _score_color
from slidebridge.utils.image import ensure_rgb
from slidebridge.utils.paths import ensure_parent


def render_view(
    slide: Slide,
    out_path: str | Path,
    patch_table: PatchTable | None = None,
    annotation_table: AnnotationTable | None = None,
    center_x: float | None = None,
    center_y: float | None = None,
    window_width: int = 4096,
    window_height: int = 3072,
    out_width: int = 1600,
    out_height: int | None = None,
    scale: float | None = None,
    magnification: float | None = None,
    opacity: float = 0.45,
    show_labels: bool = False,
    annotation_opacity: float = 0.35,
    draw_annotation_labels: bool = False,
    raster_heatmap_path: str | Path | None = None,
    raster_heatmap: RasterHeatmap | None = None,
    raster_heatmap_opacity: float | None = None,
    max_raster_heatmap_size: int = 4096,
    raster_heatmap_threshold: float | None = None,
    raster_heatmap_invert: bool = False,
    raster_heatmap_colormap: str = "auto",
    image_format: str | None = None,
    jpeg_quality: int = 90,
) -> dict[str, Any]:
    composed, result = render_view_to_image(
        slide,
        patch_table=patch_table,
        annotation_table=annotation_table,
        center_x=center_x,
        center_y=center_y,
        window_width=window_width,
        window_height=window_height,
        out_width=out_width,
        out_height=out_height,
        scale=scale,
        magnification=magnification,
        opacity=opacity,
        show_labels=show_labels,
        annotation_opacity=annotation_opacity,
        draw_annotation_labels=draw_annotation_labels,
        raster_heatmap_path=raster_heatmap_path,
        raster_heatmap=raster_heatmap,
        raster_heatmap_opacity=raster_heatmap_opacity,
        max_raster_heatmap_size=max_raster_heatmap_size,
        raster_heatmap_threshold=raster_heatmap_threshold,
        raster_heatmap_invert=raster_heatmap_invert,
        raster_heatmap_colormap=raster_heatmap_colormap,
    )
    output = ensure_parent(out_path)
    fmt = _format_from_path(output, image_format)
    if fmt == "JPEG":
        composed.save(output, format=fmt, quality=int(jpeg_quality))
    else:
        composed.save(output, format=fmt)
    result["output_path"] = str(output)
    return result


def render_view_to_image(
    slide: Slide,
    patch_table: PatchTable | None = None,
    annotation_table: AnnotationTable | None = None,
    center_x: float | None = None,
    center_y: float | None = None,
    window_width: int = 4096,
    window_height: int = 3072,
    out_width: int = 1600,
    out_height: int | None = None,
    scale: float | None = None,
    magnification: float | None = None,
    opacity: float = 0.45,
    show_labels: bool = False,
    annotation_opacity: float = 0.35,
    draw_annotation_labels: bool = False,
    raster_heatmap_path: str | Path | None = None,
    raster_heatmap: RasterHeatmap | None = None,
    raster_heatmap_opacity: float | None = None,
    max_raster_heatmap_size: int = 4096,
    raster_heatmap_threshold: float | None = None,
    raster_heatmap_invert: bool = False,
    raster_heatmap_colormap: str = "auto",
) -> tuple[Image.Image, dict[str, Any]]:
    slide_width, slide_height = slide.dimensions
    out_width = max(1, int(out_width))
    if scale is not None and magnification is not None:
        raise ValueError("Use either --scale or --magnification, not both.")
    if magnification is not None:
        base = slide.objective_power
        if base is None or float(base) <= 0:
            raise ValueError("--magnification requires slide objective_power metadata.")
        scale = float(magnification) / float(base)
    if scale is not None:
        if float(scale) <= 0:
            raise ValueError("--scale must be positive.")
        window_width = max(1, int(round(out_width / float(scale))))
        if out_height is None:
            out_height = max(1, int(round(max(1, int(window_height)) * out_width / max(1, int(window_width)))))
        window_height = max(1, int(round(int(out_height) / float(scale))))
    else:
        window_width = max(1, int(window_width))
        window_height = max(1, int(window_height))
        if out_height is None:
            out_height = max(1, int(round(window_height * out_width / float(window_width))))
    out_height = max(1, int(out_height))

    cx = float(slide_width / 2 if center_x is None else center_x)
    cy = float(slide_height / 2 if center_y is None else center_y)
    x0 = int(round(cx - window_width / 2))
    y0 = int(round(cy - window_height / 2))
    x0 = max(0, min(x0, max(0, slide_width - window_width)))
    y0 = max(0, min(y0, max(0, slide_height - window_height)))
    crop_width = max(1, min(window_width, slide_width - x0))
    crop_height = max(1, min(window_height, slide_height - y0))
    x1 = x0 + crop_width
    y1 = y0 + crop_height

    read_level = _render_read_level(slide, crop_width, crop_height, out_width, out_height)
    level_downsample = _level_downsample(slide, read_level)
    read_width = max(1, int(round(crop_width / level_downsample)))
    read_height = max(1, int(round(crop_height / level_downsample)))
    base_region = ensure_rgb(slide.read_region(x0, y0, read_width, read_height, level=read_level))
    base = base_region.resize((out_width, out_height), Image.Resampling.BILINEAR)
    scale_x = out_width / float(crop_width)
    scale_y = out_height / float(crop_height)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    patch_table = patch_table or PatchTable(records=[])
    annotation_table = annotation_table or AnnotationTable(records=[])
    has_scores = any(record.score is not None for record in patch_table.records)
    alpha = int(max(0.0, min(1.0, float(opacity))) * 255)
    rendered_patches = 0
    raster_summary = None

    if raster_heatmap_path is not None or raster_heatmap is not None:
        base, raster_summary = _composite_view_raster_heatmap(
            base,
            raster_heatmap_path,
            raster_heatmap,
            slide_width,
            slide_height,
            (x0, y0, x1, y1),
            opacity=opacity if raster_heatmap_opacity is None else raster_heatmap_opacity,
            max_size=max_raster_heatmap_size,
            threshold=raster_heatmap_threshold,
            invert=raster_heatmap_invert,
            colormap=raster_heatmap_colormap,
        )

    for record in patch_table.records:
        bbox = (record.x, record.y, record.x + record.width, record.y + record.height)
        if not _bbox_intersects(bbox, (x0, y0, x1, y1)):
            continue
        box = _bbox_to_output_box(bbox, x0, y0, scale_x, scale_y, out_width, out_height)
        if has_scores and record.score is not None:
            draw.rectangle(box, fill=_score_color(record.score, alpha))
        else:
            draw.rectangle(box, outline=(230, 70, 70, 220), width=2)
        if show_labels:
            label = record.label or ("" if record.index is None else str(record.index))
            if label:
                draw.text((box[0] + 2, box[1] + 2), label, fill=(30, 30, 30, 220))
        rendered_patches += 1

    view_annotations = _shift_annotation_table(annotation_table, x0, y0)
    rendered_annotations = draw_annotations(
        draw,
        view_annotations,
        scale_x,
        scale_y,
        opacity=annotation_opacity,
        draw_labels=draw_annotation_labels,
    )

    composed = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    return composed, {
        "input_slide": str(slide.path),
        "output_path": None,
        "view_bbox": [x0, y0, x1, y1],
        "center_x": x0 + crop_width / 2,
        "center_y": y0 + crop_height / 2,
        "window_width": crop_width,
        "window_height": crop_height,
        "out_width": out_width,
        "out_height": out_height,
        "read_level": read_level,
        "read_level_downsample": level_downsample,
        "scale": out_width / float(crop_width),
        "patches_count": len(patch_table),
        "rendered_patches_count": rendered_patches,
        "annotations_count": len(annotation_table),
        "rendered_annotations_count": rendered_annotations,
        "raster_heatmap": raster_summary,
        "has_scores": has_scores,
    }


def _bbox_intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def _bbox_to_output_box(
    bbox: tuple[float, float, float, float],
    x0: int,
    y0: int,
    scale_x: float,
    scale_y: float,
    out_width: int,
    out_height: int,
) -> tuple[int, int, int, int]:
    left = int(round((bbox[0] - x0) * scale_x))
    top = int(round((bbox[1] - y0) * scale_y))
    right = int(round((bbox[2] - x0) * scale_x))
    bottom = int(round((bbox[3] - y0) * scale_y))
    return (
        max(0, min(out_width - 1, left)),
        max(0, min(out_height - 1, top)),
        max(0, min(out_width - 1, max(right, left + 1))),
        max(0, min(out_height - 1, max(bottom, top + 1))),
    )


def _composite_view_raster_heatmap(
    base: Image.Image,
    path: str | Path | None,
    heatmap: RasterHeatmap | None,
    slide_width: int,
    slide_height: int,
    view_bbox: tuple[int, int, int, int],
    opacity: float,
    max_size: int,
    threshold: float | None,
    invert: bool,
    colormap: str,
) -> tuple[Image.Image, dict[str, Any]]:
    if heatmap is None:
        if path is None:
            raise ValueError("Raster heatmap path or loaded raster heatmap is required.")
        heatmap = load_raster_heatmap(path, max_size=max_size, threshold=threshold, invert=invert, colormap=colormap)
    hx0 = int(round(view_bbox[0] / max(1, slide_width) * heatmap.image.width))
    hy0 = int(round(view_bbox[1] / max(1, slide_height) * heatmap.image.height))
    hx1 = int(round(view_bbox[2] / max(1, slide_width) * heatmap.image.width))
    hy1 = int(round(view_bbox[3] / max(1, slide_height) * heatmap.image.height))
    heatmap_box = (
        max(0, min(heatmap.image.width - 1, hx0)),
        max(0, min(heatmap.image.height - 1, hy0)),
        max(1, min(heatmap.image.width, max(hx1, hx0 + 1))),
        max(1, min(heatmap.image.height, max(hy1, hy0 + 1))),
    )
    overlay = heatmap.image.crop(heatmap_box).resize(base.size, Image.Resampling.BILINEAR).convert("RGBA")
    alpha = overlay.getchannel("A")
    alpha = alpha.point(lambda value: int(value * max(0.0, min(1.0, float(opacity)))))
    overlay.putalpha(alpha)
    composed = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    return composed, heatmap.summary(slide_width=slide_width, slide_height=slide_height)


def _render_read_level(slide: Slide, crop_width: int, crop_height: int, out_width: int, out_height: int) -> int:
    downsample = max(float(crop_width) / max(1, out_width), float(crop_height) / max(1, out_height))
    if downsample <= 1.25:
        return 0
    try:
        level = int(slide.get_best_level_for_downsample(downsample))
    except Exception:
        return 0
    return max(0, min(level, max(0, int(slide.level_count) - 1)))


def _level_downsample(slide: Slide, level: int) -> float:
    try:
        value = float(slide.level_downsamples[int(level)])
    except Exception:
        return 1.0
    return value if value > 0 else 1.0


def _shift_annotation_table(table: AnnotationTable, x0: float, y0: float) -> AnnotationTable:
    shifted: list[AnnotationRecord] = []
    for record in table.compute_bboxes().normalize_colors().records:
        bbox = None
        if record.bbox:
            bbox = (record.bbox[0] - x0, record.bbox[1] - y0, record.bbox[2] - x0, record.bbox[3] - y0)
        shifted.append(
            AnnotationRecord(
                id=record.id,
                type=record.type,
                coordinates=_shift_coordinates(record.type, record.coordinates, x0, y0),
                label=record.label,
                color=record.color,
                confidence=record.confidence,
                source=record.source,
                properties=dict(record.properties),
                bbox=bbox,
            )
        )
    return AnnotationTable(
        records=shifted,
        source=table.source,
        source_format=table.source_format,
        coordinate_space=table.coordinate_space,
        metadata=table.metadata,
    )


def _shift_coordinates(record_type: str, coordinates: Any, x0: float, y0: float) -> Any:
    if record_type == "rectangle":
        return {
            "x": float(coordinates.get("x", 0)) - x0,
            "y": float(coordinates.get("y", 0)) - y0,
            "width": float(coordinates.get("width", 0)),
            "height": float(coordinates.get("height", 0)),
        }
    if record_type == "point":
        return {"x": float(coordinates.get("x", 0)) - x0, "y": float(coordinates.get("y", 0)) - y0}
    if record_type == "line":
        return [[float(x) - x0, float(y) - y0] for x, y in coordinates]
    if record_type == "polygon":
        return _shift_polygon(coordinates, x0, y0)
    if record_type == "multipolygon":
        return [_shift_polygon(polygon, x0, y0) for polygon in coordinates]
    return coordinates


def _shift_polygon(polygon: Any, x0: float, y0: float) -> list[list[list[float]]]:
    return [[[float(x) - x0, float(y) - y0] for x, y in ring] for ring in polygon]
