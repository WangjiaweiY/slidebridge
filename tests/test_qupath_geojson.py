from __future__ import annotations

import json

from slidebridge.annotations.qupath import load_qupath_geojson


def test_qupath_feature_collection_polygon(tmp_path):
    path = tmp_path / "annotations.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": "a",
                        "geometry": {"type": "Polygon", "coordinates": [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]]},
                        "properties": {"classification": {"name": "Tumor", "color": 0xFF0000}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    table = load_qupath_geojson(path)

    assert len(table) == 1
    assert table.records[0].label == "Tumor"
    assert table.records[0].color == "#ff0000"


def test_qupath_feature_list_and_multipolygon(tmp_path):
    path = tmp_path / "annotations.geojson"
    payload = [
        {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]],
                    [[(20, 20), (30, 20), (30, 30), (20, 30), (20, 20)]],
                ],
            },
            "properties": {"name": "Stroma", "color": "#00ff00"},
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")

    table = load_qupath_geojson(path)

    assert table.records[0].type == "multipolygon"
    assert table.records[0].label == "Stroma"


def test_qupath_unsupported_geometry_warning(tmp_path):
    path = tmp_path / "annotations.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "Feature",
                "geometry": {"type": "CircularString", "coordinates": []},
                "properties": {"name": "Unsupported"},
            }
        ),
        encoding="utf-8",
    )

    table = load_qupath_geojson(path)

    assert len(table) == 0
    assert "unsupported_geometry:CircularString" in table.summary()["warnings"]
