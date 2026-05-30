from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from slidebridge.annotations.render import draw_annotations
from slidebridge.annotations.table import AnnotationTable
from slidebridge.core.protocol import Slide
from slidebridge.overlays.patch_table import PatchTable
from slidebridge.utils.image import ensure_rgb
from slidebridge.utils.paths import ensure_parent


def render_overlay(
    slide: Slide,
    patch_table: PatchTable | None,
    out_path: str | Path,
    annotation_table: AnnotationTable | None = None,
    max_size: int = 1600,
    opacity: float = 0.45,
    show_labels: bool = False,
    annotation_opacity: float = 0.35,
    draw_annotation_labels: bool = False,
    image_format: str | None = None,
) -> dict[str, Any]:
    thumbnail = ensure_rgb(slide.get_thumbnail(max_size=max_size))
    slide_width, slide_height = slide.dimensions
    thumb_width, thumb_height = thumbnail.size
    scale_x = thumb_width / slide_width
    scale_y = thumb_height / slide_height
    overlay = Image.new("RGBA", thumbnail.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    patch_table = patch_table or PatchTable(records=[])
    annotation_table = annotation_table or AnnotationTable(records=[])
    has_scores = any(record.score is not None for record in patch_table.records)
    alpha = int(max(0.0, min(1.0, float(opacity))) * 255)
    rendered = 0

    for record in patch_table.records:
        x1 = int(round(record.x * scale_x))
        y1 = int(round(record.y * scale_y))
        x2 = int(round((record.x + record.width) * scale_x))
        y2 = int(round((record.y + record.height) * scale_y))
        if x2 < 0 or y2 < 0 or x1 >= thumb_width or y1 >= thumb_height:
            continue
        box = (
            max(0, x1),
            max(0, y1),
            min(thumb_width - 1, max(x2, x1 + 1)),
            min(thumb_height - 1, max(y2, y1 + 1)),
        )
        if has_scores and record.score is not None:
            draw.rectangle(box, fill=_score_color(record.score, alpha))
        else:
            draw.rectangle(box, outline=(230, 70, 70, 220), width=2)
        if show_labels:
            label = record.label or ("" if record.index is None else str(record.index))
            if label:
                draw.text((box[0] + 2, box[1] + 2), label, fill=(30, 30, 30, 220))
        rendered += 1

    rendered_annotations = draw_annotations(
        draw,
        annotation_table,
        scale_x,
        scale_y,
        opacity=annotation_opacity,
        draw_labels=draw_annotation_labels,
    )

    composed = Image.alpha_composite(thumbnail.convert("RGBA"), overlay).convert("RGB")
    output = ensure_parent(out_path)
    fmt = _format_from_path(output, image_format)
    if fmt == "JPEG":
        composed.save(output, format=fmt, quality=90)
    else:
        composed.save(output, format=fmt)
    return {
        "input_slide": str(slide.path),
        "patches_count": len(patch_table),
        "rendered_patches_count": rendered,
        "annotations_count": len(annotation_table),
        "rendered_annotations_count": rendered_annotations,
        "output_path": str(output),
        "has_scores": has_scores,
    }


def _score_color(score: float, alpha: int) -> tuple[int, int, int, int]:
    value = max(0.0, min(1.0, float(score)))
    if value < 0.5:
        t = value / 0.5
        r = round(48 + (245 - 48) * t)
        g = round(112 + (211 - 112) * t)
        b = round(210 + (84 - 210) * t)
    else:
        t = (value - 0.5) / 0.5
        r = round(245 + (220 - 245) * t)
        g = round(211 + (48 - 211) * t)
        b = round(84 + (48 - 84) * t)
    return int(r), int(g), int(b), int(alpha)


def _format_from_path(path: Path, requested: str | None) -> str:
    if requested:
        fmt = requested.lower()
    else:
        fmt = path.suffix.lower().lstrip(".") or "png"
    if fmt in {"jpg", "jpeg"}:
        return "JPEG"
    if fmt == "png":
        return "PNG"
    raise ValueError("Output format must be png or jpg")
