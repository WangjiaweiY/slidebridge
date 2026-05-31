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

    asset = client.get("/static/vendor/openseadragon/openseadragon.min.js")
    assert asset.status_code == 200
    assert "OpenSeadragon" in asset.text

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


def test_server_directory_viewer_lists_and_serves_multiple_slides(tmp_path):
    create_demo_slide(tmp_path / "demo_a.png", width=512, height=384, seed=3)
    nested = tmp_path / "nested"
    nested.mkdir()
    create_demo_slide(nested / "demo_b.png", width=640, height=512, seed=4)

    app = create_app(tmp_path, reader="image", recursive=True, tile_size=128)
    client = TestClient(app)

    slides = client.get("/api/slides")
    assert slides.status_code == 200
    payload = slides.json()
    assert payload["library_mode"] is True
    assert payload["recursive"] is True
    assert payload["count"] == 2

    page = client.get("/")
    assert page.status_code == 200
    assert "Slide Library" in page.text
    assert "scan scope" in page.text
    assert "selected slide" in page.text
    assert "sidebar-tabs" in page.text
    assert "language-toggle" in page.text
    assert "data-i18n=\"slideMetadata\"" in page.text
    assert "flex-direction: column" in page.text
    assert "overflow-y: auto" in page.text
    assert "syncLibraryListHeight" not in page.text
    assert "setupSlideListScroll" not in page.text

    info = client.get("/api/info?slide_id=1")
    assert info.status_code == 200
    assert info.json()["reader"] == "image"
    assert info.json()["relative_path"].startswith("nested")
    assert info.json()["library_root"] == str(tmp_path)

    dzi = client.get("/slides/1/dzi.dzi")
    assert dzi.status_code == 200
    assert "TileSize=\"128\"" in dzi.text

    tile = client.get("/slides/1/dzi_files/10/0_0.jpeg")
    assert tile.status_code == 200
    assert tile.headers["content-type"] == "image/jpeg"


def test_server_remote_context_is_rendered(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=256, seed=5)
    app = create_app(
        slide_path,
        reader="image",
        viewer_context="remote",
        viewer_remote_user="user",
        viewer_remote_host="server",
        viewer_remote_ssh_port=2222,
        viewer_source="/data/slides/demo.png",
    )
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "remote SSH" in response.text
    assert "user" in response.text
    assert "server" in response.text
    assert "2222" in response.text
    assert "/data/slides/demo.png" in response.text
