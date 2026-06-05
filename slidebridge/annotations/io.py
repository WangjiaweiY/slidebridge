from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from slidebridge.annotations.aperio import load_aperio_xml
from slidebridge.annotations.asap import load_asap_xml
from slidebridge.annotations.qupath import load_qupath_geojson
from slidebridge.annotations.table import AnnotationRecord, AnnotationTable
from slidebridge.utils.paths import ensure_parent


def load_annotation_table(path: str | Path, format: str | None = None) -> AnnotationTable:
    annotation_path = Path(path)
    fmt = _infer_format(annotation_path, format)
    if fmt in {"qupath-geojson", "geojson"}:
        return load_qupath_geojson(annotation_path)
    if fmt == "asap-xml":
        return load_asap_xml(annotation_path)
    if fmt in {"aperio-xml", "imagescope-xml"}:
        return load_aperio_xml(annotation_path)
    if fmt == "slidebridge-json":
        return _load_slidebridge_json(annotation_path)
    raise ValueError(f"Unsupported annotation format: {fmt}")


def save_annotation_table(table: AnnotationTable, path: str | Path, format: str | None = None, pretty: bool = True) -> Path:
    output = ensure_parent(path)
    fmt = _infer_output_format(output, format)
    if fmt == "slidebridge-json":
        text = json.dumps(table.compute_bboxes().normalize_colors().to_jsonable(), ensure_ascii=False, indent=2 if pretty else None)
        output.write_text(text, encoding="utf-8")
        return output
    if fmt == "geojson":
        text = json.dumps(_to_geojson(table), ensure_ascii=False, indent=2 if pretty else None)
        output.write_text(text, encoding="utf-8")
        return output
    raise ValueError(f"Unsupported output annotation format: {fmt}")


def _load_slidebridge_json(path: Path) -> AnnotationTable:
    payload = json.loads(path.read_text(encoding="utf-8"))
    annotations = payload.get("annotations")
    if not isinstance(annotations, list):
        raise ValueError("SlideBridge annotation JSON must contain an 'annotations' list")
    records = []
    for item in annotations:
        bbox = item.get("bbox")
        records.append(
            AnnotationRecord(
                id=item.get("id"),
                type=item.get("type", "unknown"),
                coordinates=item.get("coordinates"),
                label=item.get("label"),
                color=item.get("color"),
                confidence=item.get("confidence"),
                source=item.get("source"),
                properties=item.get("properties") or {},
                bbox=None if bbox is None else tuple(float(value) for value in bbox),
            )
        )
    return AnnotationTable(
        records=records,
        source=str(path),
        source_format="slidebridge-json",
        coordinate_space=payload.get("coordinate_space", "level0"),
        metadata=payload.get("metadata") or {},
    ).compute_bboxes().normalize_colors()


def _to_geojson(table: AnnotationTable) -> dict[str, Any]:
    features = []
    for record in table.compute_bboxes().normalize_colors().records:
        geometry = _record_to_geojson_geometry(record)
        if geometry is None:
            continue
        features.append(
            {
                "type": "Feature",
                "id": record.id,
                "geometry": geometry,
                "properties": {
                    "label": record.label,
                    "color": record.color,
                    "id": record.id,
                    "source": record.source,
                    "original_properties": record.properties,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "properties": {"coordinate_space": table.coordinate_space},
        "features": features,
    }


def _record_to_geojson_geometry(record: AnnotationRecord) -> dict[str, Any] | None:
    if record.type == "polygon":
        return {"type": "Polygon", "coordinates": record.coordinates}
    if record.type == "multipolygon":
        return {"type": "MultiPolygon", "coordinates": record.coordinates}
    if record.type == "rectangle":
        rect = record.coordinates
        x = float(rect["x"])
        y = float(rect["y"])
        w = float(rect["width"])
        h = float(rect["height"])
        return {"type": "Polygon", "coordinates": [[(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]]}
    if record.type == "point":
        return {"type": "Point", "coordinates": [record.coordinates["x"], record.coordinates["y"]]}
    if record.type == "line":
        return {"type": "LineString", "coordinates": record.coordinates}
    return None


def _infer_format(path: Path, requested: str | None) -> str:
    if requested:
        return requested.lower()
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name.endswith(".annotations.json") or name.endswith(".slidebridge.json"):
        return "slidebridge-json"
    if suffix in {".geojson"}:
        return "qupath-geojson"
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("type") == "SlideBridgeAnnotationTable":
            return "slidebridge-json"
        return "geojson"
    if suffix == ".xml":
        if _looks_like_aperio_xml(path):
            return "aperio-xml"
        return "asap-xml"
    raise ValueError(f"Cannot infer annotation format from: {path}")


def _infer_output_format(path: Path, requested: str | None) -> str:
    if requested:
        return requested.lower()
    name = path.name.lower()
    if name.endswith(".geojson"):
        return "geojson"
    if name.endswith(".json"):
        return "slidebridge-json"
    raise ValueError("Cannot infer output annotation format. Use --output-format.")


def _looks_like_aperio_xml(path: Path) -> bool:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return False
    return bool(root.findall(".//Region/Vertices/Vertex"))
