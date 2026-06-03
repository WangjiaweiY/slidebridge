from __future__ import annotations

import re

from fastapi.testclient import TestClient
from PIL import Image

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
    assert info.headers["cache-control"] == "no-store"

    patches = client.get("/api/patches")
    assert patches.status_code == 200
    assert patches.json()["patches"][0]["score"] == 0.5
    assert patches.json()["count"] == 1
    assert patches.json()["has_scores"] is True
    assert patches.headers["cache-control"] == "no-store"

    dzi = client.get("/dzi.dzi")
    assert dzi.status_code == 200
    assert "TileSize=\"128\"" in dzi.text

    tile = client.get("/dzi_files/9/0_0.jpeg")
    assert tile.status_code == 200
    assert tile.headers["cache-control"] == "no-store"
    assert tile.headers["content-type"] == "image/jpeg"

    page = client.get("/")
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    match = re.search(r'const tileCacheKey = "([0-9a-f]+)"', page.text)
    assert match
    assert 'fetch(apiUrl("patches"), {cache: "no-store"})' in page.text
    assert "initialTileCacheStats" in page.text
    assert "initialTilePerformanceStats" in page.text
    assert "imageLoaderLimit: 4" in page.text
    assert "maxImageCacheCount: 200" in page.text
    assert "blendTime: 0" in page.text
    assert "immediateRender: false" in page.text
    assert 'id="overlay-canvas"' in page.text
    assert "drawCanvasOverlays" in page.text
    assert "currentImageBounds(0.12)" in page.text
    assert "overlay-render-count" in page.text
    assert "snapshotOptions" in page.text
    assert "copy-viewer-url" in page.text
    assert "copy-render-command" in page.text
    assert "download-render-view" in page.text
    assert "backdrop-filter" in page.text
    assert "raster-heatmap-hidden" in page.text
    assert 'element.style.display = toggle.checked ? "block" : "none"' not in page.text
    assert "parseViewerStateFromUrl" in page.text
    assert "buildViewerUrl" in page.text
    assert "scheduleViewerStateUrlUpdate" in page.text
    assert "buildRenderViewCommand" in page.text
    assert "buildSnapshotDownloadUrl" in page.text
    cache_key = match.group(1)
    keyed_dzi = client.get(f"/slides/0/{cache_key}/dzi.dzi")
    assert keyed_dzi.status_code == 200
    keyed_tile = client.get(f"/slides/0/{cache_key}/dzi_files/9/0_0.jpeg")
    assert keyed_tile.status_code == 200
    assert keyed_tile.headers["cache-control"] == "public, max-age=3600"
    stale_tile = client.get("/slides/0/not-the-current-cache-key/dzi_files/9/0_0.jpeg")
    assert stale_tile.status_code == 404

    asset = client.get("/static/vendor/openseadragon/openseadragon.min.js")
    assert asset.status_code == 200
    assert "OpenSeadragon" in asset.text

    invalid = client.get("/dzi_files/99/0_0.jpeg")
    assert invalid.status_code == 404


def test_server_render_view_endpoint_returns_png(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=13)
    patches_path = tmp_path / "coords.csv"
    patches_path.write_text(
        "x,y,width,height,score\n200,150,64,64,0.8\n10,20,64,64,0.1\n",
        encoding="utf-8",
    )
    app = create_app(slide_path, patches_path=patches_path, reader="image", tile_size=128)
    client = TestClient(app)

    response = client.get(
        "/api/render-view",
        params={
            "center_x": 256,
            "center_y": 192,
            "window_width": 256,
            "window_height": 192,
            "out_width": 320,
            "out_height": 240,
            "score_threshold": 0.5,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"\x89PNG")
    image_path = tmp_path / "snapshot.png"
    image_path.write_bytes(response.content)
    with Image.open(image_path) as image:
        assert image.size == (320, 240)


def test_server_tile_cache_records_hits_misses_and_evictions(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=11)
    app = create_app(slide_path, reader="image", tile_size=128, tile_cache_size=2)
    client = TestClient(app)

    page = client.get("/")
    cache_key = re.search(r'const tileCacheKey = "([0-9a-f]+)"', page.text).group(1)  # type: ignore[union-attr]

    initial = client.get("/api/cache-stats")
    assert initial.status_code == 200
    assert initial.headers["cache-control"] == "no-store"
    assert initial.json()["enabled"] is True
    assert initial.json()["entries"] == 0
    assert initial.json()["max_mb"] == 256

    first = client.get(f"/slides/0/{cache_key}/dzi_files/9/0_0.jpeg")
    assert first.status_code == 200
    after_first = client.get("/api/cache-stats").json()
    assert after_first["entries"] == 1
    assert after_first["bytes"] > 0
    assert after_first["mb"] >= 0
    assert after_first["misses"] == 1
    assert after_first["hits"] == 0
    performance = client.get("/api/performance")
    assert performance.status_code == 200
    assert performance.headers["cache-control"] == "no-store"
    performance_payload = performance.json()
    assert performance_payload["tiles"]["generated_tiles"] == 1
    assert performance_payload["tiles"]["total_tile_ms"]["avg"] is not None

    second = client.get(f"/slides/0/{cache_key}/dzi_files/9/0_0.jpeg")
    assert second.status_code == 200
    after_second = client.get("/api/cache-stats").json()
    assert after_second["entries"] == 1
    assert after_second["misses"] == 1
    assert after_second["hits"] == 1
    assert client.get("/api/performance").json()["tiles"]["cache_served_tiles"] == 1

    client.get(f"/slides/0/{cache_key}/dzi_files/9/1_0.jpeg")
    client.get(f"/slides/0/{cache_key}/dzi_files/9/2_0.jpeg")
    after_eviction = client.get("/api/cache-stats").json()
    assert after_eviction["entries"] == 2
    assert after_eviction["evictions"] >= 1


def test_server_tile_cache_can_be_disabled(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=256, seed=12)
    app = create_app(slide_path, reader="image", tile_size=128, tile_cache_size=0)
    client = TestClient(app)

    page = client.get("/")
    cache_key = re.search(r'const tileCacheKey = "([0-9a-f]+)"', page.text).group(1)  # type: ignore[union-attr]
    tile = client.get(f"/slides/0/{cache_key}/dzi_files/8/0_0.jpeg")
    assert tile.status_code == 200

    stats = client.get("/api/cache-stats").json()
    assert stats["enabled"] is False
    assert stats["entries"] == 0
    assert stats["hits"] == 0
    assert stats["misses"] == 0


def test_server_raster_heatmap_endpoint(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=8)
    heatmap_path = tmp_path / "heatmap.png"
    Image.new("RGB", (64, 48), (240, 20, 20)).save(heatmap_path)
    app = create_app(
        slide_path,
        raster_heatmap_path=heatmap_path,
        reader="image",
        raster_heatmap_threshold=0.25,
        raster_heatmap_invert=True,
        raster_heatmap_colormap="score",
    )
    client = TestClient(app)

    page = client.get("/")
    match = re.search(r'const tileCacheKey = "([0-9a-f]+)"', page.text)
    assert match
    payload = client.get("/api/raster-heatmap").json()
    assert payload["available"] is True
    assert payload["mapping"] == "stretch_to_full_slide"
    assert payload["threshold"] == 0.25
    assert payload["invert"] is True
    assert payload["colormap"] == "score"
    assert payload["url"].endswith("/raster_heatmap.png")

    image = client.get(payload["url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.headers["cache-control"] == "public, max-age=3600"


def test_server_rejects_invalid_tile_config(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=256, seed=2)

    try:
        create_app(slide_path, reader="image", tile_size=0)
    except ValueError as exc:
        assert "tile_size" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid tile_size to raise")

    try:
        create_app(slide_path, reader="image", tile_cache_size=-1)
    except ValueError as exc:
        assert "tile_cache_size" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid tile_cache_size to raise")

    try:
        create_app(slide_path, reader="image", tile_cache_mb=-1)
    except ValueError as exc:
        assert "tile_cache_mb" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid tile_cache_mb to raise")

    try:
        create_app(slide_path, reader="image", tile_workers=0)
    except ValueError as exc:
        assert "tile_workers" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid tile_workers to raise")

    try:
        create_app(slide_path, reader="image", raster_heatmap_threshold=1.5)
    except ValueError as exc:
        assert "raster_heatmap_threshold" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid raster_heatmap_threshold to raise")


def test_server_directory_viewer_lists_and_serves_multiple_slides(tmp_path):
    create_demo_slide(tmp_path / "demo_a.png", width=512, height=384, seed=3)
    nested = tmp_path / "nested"
    nested.mkdir()
    create_demo_slide(nested / "demo_b.png", width=640, height=512, seed=4)

    app = create_app(tmp_path, reader="image", recursive=True, tile_size=128)
    client = TestClient(app)

    slides = client.get("/api/slides")
    assert slides.status_code == 200
    assert slides.headers["cache-control"] == "no-store"
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
    assert "zoom-control" in page.text
    assert "equiv. magnification" in page.text
    assert "zoomToImageScale" in page.text
    assert "score-threshold-slider" in page.text
    assert "top-k-input" in page.text
    assert "annotation-label-filter" in page.text
    assert "overlay-detail" in page.text
    assert "filteredPatches" in page.text
    assert "filteredAnnotations" in page.text
    assert "zoomToBbox" in page.text
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
