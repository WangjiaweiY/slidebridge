from __future__ import annotations

from fastapi.testclient import TestClient

from slidebridge.server.app import create_app
from slidebridge.utils.demo import create_demo_slide


def test_server_info_patches_dzi_and_tile(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=1)
    patches_path = tmp_path / "coords.csv"
    patches_path.write_text("x,y,width,height,score\n10,20,64,64,0.5\n", encoding="utf-8")

    app = create_app(slide_path, patches_path=patches_path, reader="image", tile_size=128, jpeg_quality=80)
    client = TestClient(app)

    info = client.get("/api/info")
    assert info.status_code == 200
    assert info.json()["reader"] == "image"

    patches = client.get("/api/patches")
    assert patches.status_code == 200
    assert patches.json()["patches"][0]["score"] == 0.5
    assert patches.json()["count"] == 1
    assert patches.json()["has_scores"] is True

    dzi = client.get("/dzi.dzi")
    assert dzi.status_code == 200
    assert "TileSize=\"128\"" in dzi.text

    tile = client.get("/dzi_files/9/0_0.jpeg")
    assert tile.status_code == 200
    assert tile.headers["cache-control"] == "public, max-age=3600"
    assert tile.headers["content-type"] == "image/jpeg"

    invalid = client.get("/dzi_files/99/0_0.jpeg")
    assert invalid.status_code == 404


def test_server_rejects_invalid_tile_config(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=256, seed=2)

    try:
        create_app(slide_path, reader="image", tile_size=0)
    except ValueError as exc:
        assert "tile_size" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid tile_size to raise")
