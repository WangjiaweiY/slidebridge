from __future__ import annotations

from fastapi.testclient import TestClient

from slidebridge.annotations.demo import create_demo_annotations
from slidebridge.server.app import create_app
from slidebridge.utils.demo import create_demo_slide


def test_viewer_annotations_api(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=1)
    annotations = create_demo_annotations(tmp_path / "annotations.geojson", width=512, height=384, seed=1)
    app = create_app(slide, annotations_path=annotations, reader="image")
    client = TestClient(app)

    response = client.get("/api/annotations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] > 0
    assert payload["coordinate_space"] == "level0"
    assert payload["annotations"][0]["bbox"] is not None


def test_viewer_with_patches_and_annotations(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=2)
    patches = tmp_path / "coords.csv"
    patches.write_text("x,y,width,height,score\n10,20,64,64,0.5\n", encoding="utf-8")
    annotations = create_demo_annotations(tmp_path / "annotations.geojson", width=512, height=384, seed=2)
    app = create_app(slide, patches_path=patches, annotations_path=annotations, reader="image")
    client = TestClient(app)

    page = client.get("/")
    annotation_payload = client.get("/api/annotations").json()
    patch_payload = client.get("/api/patches").json()

    assert page.status_code == 200
    assert "annotation overlay for research/debugging" in page.text
    assert annotation_payload["returned"] > 0
    assert patch_payload["returned"] == 1
