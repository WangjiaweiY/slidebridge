from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from slidebridge.annotations.geometry import compute_record_bbox
from slidebridge.annotations.table import AnnotationRecord, AnnotationTable, normalize_color


def load_qupath_geojson(path: str | Path) -> AnnotationTable:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    features = _features_from_payload(payload)
    records: list[AnnotationRecord] = []
    warnings: list[str] = []
    for index, feature in enumerate(features):
        for record in _records_from_feature(feature, source=str(source), fallback_id=str(index), warnings=warnings):
            records.append(record)
    table = AnnotationTable(
        records=records,
        source=str(source),
        source_format="qupath-geojson",
        metadata={"warnings": warnings} if warnings else {},
    )
    return table.compute_bboxes().normalize_colors()


def _features_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        return [feature for feature in payload.get("features", []) if isinstance(feature, dict)]
    if isinstance(payload, dict) and payload.get("type") == "Feature":
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and "geometry" in payload:
        return [{"type": "Feature", "geometry": payload.get("geometry"), "properties": payload.get("properties", {})}]
    raise ValueError("Unsupported GeoJSON payload. Expected FeatureCollection, Feature, or feature list.")


def _records_from_feature(feature: dict[str, Any], source: str, fallback_id: str, warnings: list[str]) -> list[AnnotationRecord]:
    geometry = feature.get("geometry") or {}
    properties = dict(feature.get("properties") or {})
    feature_id = str(feature.get("id") or properties.get("id") or fallback_id)
    label = _label_from_properties(properties)
    color = _color_from_properties(properties)
    return _records_from_geometry(geometry, feature_id, label, color, source, properties, warnings)


def _records_from_geometry(
    geometry: dict[str, Any],
    record_id: str,
    label: str | None,
    color: str | None,
    source: str,
    properties: dict[str, Any],
    warnings: list[str],
) -> list[AnnotationRecord]:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    records: list[AnnotationRecord] = []
    if gtype == "Polygon":
        record = AnnotationRecord(record_id, "polygon", _polygon(coords), label, color, source=source, properties=properties)
        records.append(record)
    elif gtype == "MultiPolygon":
        record = AnnotationRecord(record_id, "multipolygon", [_polygon(poly) for poly in coords or []], label, color, source=source, properties=properties)
        records.append(record)
    elif gtype == "Point":
        record = AnnotationRecord(record_id, "point", {"x": float(coords[0]), "y": float(coords[1])}, label, color, source=source, properties=properties)
        records.append(record)
    elif gtype == "MultiPoint":
        for index, point in enumerate(coords or []):
            records.append(AnnotationRecord(f"{record_id}:{index}", "point", {"x": float(point[0]), "y": float(point[1])}, label, color, source=source, properties=properties))
    elif gtype == "LineString":
        records.append(AnnotationRecord(record_id, "line", [(float(p[0]), float(p[1])) for p in coords or []], label, color, source=source, properties=properties))
    elif gtype == "GeometryCollection":
        for index, item in enumerate(geometry.get("geometries", []) or []):
            records.extend(_records_from_geometry(item, f"{record_id}:{index}", label, color, source, properties, warnings))
    else:
        warnings.append(f"unsupported_geometry:{gtype}")
    return [record.__class__(**{**record.to_dict(), "bbox": compute_record_bbox(record)}) for record in records]


def _polygon(coords: Any) -> list[list[tuple[float, float]]]:
    return [[(float(point[0]), float(point[1])) for point in ring] for ring in (coords or [])]


def _label_from_properties(properties: dict[str, Any]) -> str | None:
    classification = properties.get("classification")
    if isinstance(classification, dict) and classification.get("name"):
        return str(classification["name"])
    for key in ("label", "name", "pathClass", "objectType"):
        value = properties.get(key)
        if value:
            return str(value)
    return None


def _color_from_properties(properties: dict[str, Any]) -> str | None:
    classification = properties.get("classification")
    if isinstance(classification, dict) and classification.get("color") is not None:
        return normalize_color(classification.get("color"))
    return normalize_color(properties.get("color"))
