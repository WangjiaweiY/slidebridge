from __future__ import annotations

from typing import Any

from PIL import ImageDraw

from slidebridge.annotations.table import AnnotationRecord, AnnotationTable


def draw_annotations(
    draw: ImageDraw.ImageDraw,
    table: AnnotationTable,
    scale_x: float,
    scale_y: float,
    opacity: float = 0.35,
    draw_labels: bool = False,
) -> int:
    alpha = int(max(0.0, min(1.0, float(opacity))) * 255)
    rendered = 0
    for record in table.compute_bboxes().normalize_colors().records:
        color = _rgba(record.color or "#e41a1c", alpha)
        outline = _rgba(record.color or "#e41a1c", 240)
        if record.type == "polygon":
            rendered += _draw_polygon(draw, record.coordinates, scale_x, scale_y, color, outline)
        elif record.type == "multipolygon":
            for polygon in record.coordinates:
                rendered += _draw_polygon(draw, polygon, scale_x, scale_y, color, outline)
        elif record.type == "rectangle":
            rect = record.coordinates
            box = (
                int(rect["x"] * scale_x),
                int(rect["y"] * scale_y),
                int((rect["x"] + rect["width"]) * scale_x),
                int((rect["y"] + rect["height"]) * scale_y),
            )
            draw.rectangle(box, outline=outline, fill=color, width=2)
            rendered += 1
        elif record.type == "point":
            x = int(record.coordinates["x"] * scale_x)
            y = int(record.coordinates["y"] * scale_y)
            r = 4
            draw.ellipse((x - r, y - r, x + r, y + r), fill=outline)
            rendered += 1
        elif record.type == "line":
            points = [(int(x * scale_x), int(y * scale_y)) for x, y in record.coordinates]
            if len(points) >= 2:
                draw.line(points, fill=outline, width=2)
                rendered += 1
        if draw_labels and record.label and record.bbox:
            draw.text((int(record.bbox[0] * scale_x) + 2, int(record.bbox[1] * scale_y) + 2), record.label, fill=outline)
    return rendered


def _draw_polygon(draw: ImageDraw.ImageDraw, rings: Any, scale_x: float, scale_y: float, color: tuple[int, int, int, int], outline: tuple[int, int, int, int]) -> int:
    if not rings:
        return 0
    exterior = [(int(x * scale_x), int(y * scale_y)) for x, y in rings[0]]
    if len(exterior) >= 3:
        draw.polygon(exterior, fill=color, outline=outline)
        for hole in rings[1:]:
            points = [(int(x * scale_x), int(y * scale_y)) for x, y in hole]
            if len(points) >= 3:
                draw.polygon(points, fill=(0, 0, 0, 0), outline=outline)
        return 1
    return 0


def _rgba(hex_color: str, alpha: int) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    try:
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), int(alpha)
    except (ValueError, IndexError):
        return 228, 26, 28, int(alpha)
