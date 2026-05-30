from __future__ import annotations

import json

from slidebridge.annotations.io import load_annotation_table, save_annotation_table
from slidebridge.annotations.table import AnnotationRecord, AnnotationTable


def test_load_annotation_table_auto_detect_geojson(tmp_path):
    path = tmp_path / "a.geojson"
    path.write_text(
        json.dumps({"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}, "properties": {"name": "Dot"}}),
        encoding="utf-8",
    )

    table = load_annotation_table(path)

    assert table.source_format == "qupath-geojson"
    assert table.records[0].label == "Dot"


def test_save_and_load_slidebridge_json(tmp_path):
    table = AnnotationTable([AnnotationRecord("a", "point", {"x": 1, "y": 2}, "Tumor", "#ff0000")])
    out = tmp_path / "a.slidebridge.json"

    save_annotation_table(table, out, format="slidebridge-json")
    loaded = load_annotation_table(out)

    assert loaded.source_format == "slidebridge-json"
    assert loaded.records[0].label == "Tumor"


def test_save_geojson(tmp_path):
    table = AnnotationTable([AnnotationRecord("a", "rectangle", {"x": 1, "y": 2, "width": 3, "height": 4}, "Tumor")])
    out = tmp_path / "a.geojson"

    save_annotation_table(table, out, format="geojson")
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["type"] == "FeatureCollection"
    assert payload["features"][0]["geometry"]["type"] == "Polygon"
