from __future__ import annotations

from importlib import resources

from fastapi.testclient import TestClient

import slidebridge
from slidebridge.server.app import create_app
from slidebridge.utils.demo import create_demo_slide


def test_viewer_template_is_packaged():
    template = resources.files("slidebridge.server.templates").joinpath("viewer.html")

    assert template.is_file()
    assert "OpenSeadragon" in template.read_text(encoding="utf-8")


def test_openseadragon_asset_is_packaged():
    static_root = resources.files("slidebridge.server").joinpath("static")
    asset = static_root.joinpath("vendor", "openseadragon", "openseadragon.min.js")
    license_file = static_root.joinpath("vendor", "openseadragon", "LICENSE.txt")
    image = static_root.joinpath("vendor", "openseadragon", "images", "zoomin_rest.png")

    assert asset.is_file()
    assert license_file.is_file()
    assert image.is_file()


def test_viewer_index_returns_html(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=13)
    app = create_app(slide, reader="image")
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "SlideBridge Viewer" in response.text
    assert "/static/vendor/openseadragon/openseadragon.min.js" in response.text
    assert slidebridge.__version__ == "0.2.14"
