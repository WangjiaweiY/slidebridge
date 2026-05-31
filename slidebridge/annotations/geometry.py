from __future__ import annotations

from typing import Any

from slidebridge.annotations.table import AnnotationRecord


def compute_polygon_bbox(rings: list[list[tuple[float, float]]]) -> tuple[float, float, float, float] | None:
    points = [point for ring in rings for point in ring]
    if not points:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def compute_record_bbox(record: AnnotationRecord) -> tuple[float, float, float, float] | None:
    try:
        if record.type == "polygon":
            return compute_polygon_bbox(record.coordinates)
        if record.type == "multipolygon":
            bboxes = [compute_polygon_bbox(polygon) for polygon in record.coordinates]
            valid = [bbox for bbox in bboxes if bbox is not None]
            if not valid:
                return None
            return min(b[0] for b in valid), min(b[1] for b in valid), max(b[2] for b in valid), max(b[3] for b in valid)
        if record.type == "rectangle":
            rect = record.coordinates
            x = float(rect["x"])
            y = float(rect["y"])
            return x, y, x + float(rect["width"]), y + float(rect["height"])
        if record.type == "point":
            x = float(record.coordinates["x"])
            y = float(record.coordinates["y"])
            return x, y, x, y
        if record.type == "line":
            points = record.coordinates or []
            if not points:
                return None
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            return min(xs), min(ys), max(xs), max(ys)
    except (TypeError, ValueError, KeyError):
        return None
    return None


def point_in_polygon(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    if len(ring) < 3:
        return False
    inside = False
    px = float(x)
    py = float(y)
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = float(point[0]), float(point[1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        intersects = (yi > py) != (yj > py)
        if intersects:
            x_cross = (xj - xi) * (py - yi) / ((yj - yi) or 1e-12) + xi
            if px < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_record(x: float, y: float, record: AnnotationRecord) -> bool:
    try:
        if record.type == "polygon":
            return _point_in_polygon_with_holes(x, y, record.coordinates)
        if record.type == "multipolygon":
            return any(_point_in_polygon_with_holes(x, y, polygon) for polygon in record.coordinates)
        if record.type == "rectangle":
            rect = record.coordinates
            return float(rect["x"]) <= x <= float(rect["x"]) + float(rect["width"]) and float(rect["y"]) <= y <= float(rect["y"]) + float(rect["height"])
        if record.type == "point":
            return float(record.coordinates["x"]) == float(x) and float(record.coordinates["y"]) == float(y)
        if record.bbox is not None:
            return bbox_contains_point(record.bbox, x, y)
    except (TypeError, KeyError, ValueError):
        return False
    return False


def bbox_intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def bbox_contains_point(bbox: tuple[float, float, float, float], x: float, y: float) -> bool:
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def polygon_area(ring: list[tuple[float, float]]) -> float:
    if len(ring) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(ring):
        x1, y1 = float(point[0]), float(point[1])
        x2, y2 = float(ring[(index + 1) % len(ring)][0]), float(ring[(index + 1) % len(ring)][1])
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def record_area(record: AnnotationRecord) -> float | None:
    try:
        if record.type == "polygon":
            exterior = polygon_area(record.coordinates[0])
            holes = sum(polygon_area(ring) for ring in record.coordinates[1:])
            return max(0.0, exterior - holes)
        if record.type == "multipolygon":
            return sum(record_area(AnnotationRecord(type="polygon", coordinates=polygon)) or 0.0 for polygon in record.coordinates)
        if record.type == "rectangle":
            return abs(float(record.coordinates["width"]) * float(record.coordinates["height"]))
    except (TypeError, KeyError, ValueError, IndexError):
        return None
    return None


def _point_in_polygon_with_holes(x: float, y: float, rings: Any) -> bool:
    if not rings:
        return False
    if not point_in_polygon(x, y, rings[0]):
        return False
    return not any(point_in_polygon(x, y, hole) for hole in rings[1:])
