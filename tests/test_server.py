from __future__ import annotations

import json
import re
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from slidebridge.server.app import create_app
from slidebridge.utils.demo import create_demo_slide


def _viewer_config(page_text: str) -> dict:
    match = re.search(
        r'<script id="slidebridge-viewer-config" type="application/json">(.*?)</script>',
        page_text,
        flags=re.DOTALL,
    )
    assert match
    return json.loads(match.group(1))


def _viewer_static_text(client: TestClient) -> tuple[str, str, str]:
    js = client.get("/static/viewer.js")
    css = client.get("/static/viewer.css")
    figure_js = client.get("/static/viewer_figure.js")

    assert js.status_code == 200
    assert css.status_code == 200
    assert figure_js.status_code == 200
    return js.text, css.text, figure_js.text


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
    viewer_config = _viewer_config(page.text)
    assert re.fullmatch(r"[0-9a-f]+", viewer_config["tileCacheKey"])
    assert "/static/viewer.css" in page.text
    assert "/static/viewer.js" in page.text
    assert "/static/viewer_figure.js" in page.text
    assert "figure-tab" in page.text
    viewer_js, viewer_css, viewer_figure_js = _viewer_static_text(client)
    viewer_assets = viewer_js + viewer_css + viewer_figure_js
    assert 'fetch(apiUrl("patches"), {cache: "no-store"})' in viewer_js
    assert "initialTileCacheStats" in viewer_js
    assert "initialTilePerformanceStats" in viewer_js
    assert "imageLoaderLimit: 4" in viewer_js
    assert "maxImageCacheCount: 200" in viewer_js
    assert "blendTime: 0" in viewer_js
    assert "immediateRender: false" in viewer_js
    assert 'id="overlay-canvas"' in page.text
    assert "drawCanvasOverlays" in viewer_js
    assert "currentImageBounds(0.12)" in viewer_js
    assert "overlay-render-count" in page.text
    assert "snapshotOptions" in viewer_js
    assert "copy-viewer-url" in page.text
    assert "copy-render-command" in page.text
    assert "download-render-view" in page.text
    assert "backdrop-filter" in viewer_css
    assert "raster-heatmap-hidden" in viewer_assets
    assert "overlay.style.backgroundImage" in viewer_js
    assert 'fetch(apiUrl("raster-heatmaps"), {cache: "no-store"})' in viewer_js
    assert "rasterHeatmapElements = new Map()" in viewer_js
    assert "rasterHeatmapLayerState = new Map()" in viewer_js
    assert "raster-heatmap-layer-list" in page.text
    assert "renderRasterHeatmap();" in viewer_js
    assert "image.src = rasterHeatmapPayload.url" not in viewer_js
    assert "object-fit: fill" not in viewer_css
    assert 'element.style.display = toggle.checked ? "block" : "none"' not in viewer_js
    assert "parseViewerStateFromUrl" in viewer_js
    assert "buildViewerUrl" in viewer_js
    assert "scheduleViewerStateUrlUpdate" in viewer_js
    assert "buildRenderViewCommand" in viewer_js
    assert "buildSnapshotDownloadUrl" in viewer_js
    assert "SlideBridgeViewer" in viewer_js
    assert "selectSquareRegion" in viewer_js
    assert 'fetch("/api/render-figure"' in viewer_figure_js
    cache_key = viewer_config["tileCacheKey"]
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


def test_server_render_figure_endpoint_returns_png(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=14)
    app = create_app(slide_path, reader="image", tile_size=128)
    client = TestClient(app)
    spec = {
        "slide_id": 0,
        "canvas": {"width": 2400, "height": 1800, "background": "white"},
        "heatmap_layer_id": "",
        "overlay_opacity": 0.45,
        "main": {"bbox": [64, 48, 448, 336], "mode": "raw", "label": "A", "scalebar_um": None},
        "patches": [{"slot": 0, "bbox": [100, 80, 180, 160], "mode": "raw", "label": "B"}],
    }

    response = client.post("/api/render-figure", json=spec)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"\x89PNG")
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (2400, 1800)


def test_server_render_figure_uses_selected_raster_heatmap_layer(tmp_path):
    slide_path = tmp_path / "white.png"
    Image.new("RGB", (512, 384), (255, 255, 255)).save(slide_path)
    low_path = tmp_path / "low.png"
    high_path = tmp_path / "high.png"
    Image.new("RGB", (64, 48), (20, 40, 240)).save(low_path)
    Image.new("RGB", (64, 48), (240, 40, 20)).save(high_path)
    app = create_app(
        slide_path,
        raster_heatmap_path=low_path,
        raster_heatmap_layers=[{"name": "high", "path": str(high_path)}],
        reader="image",
    )
    client = TestClient(app)
    spec = {
        "slide_id": 0,
        "canvas": {"width": 2400, "height": 1800, "background": "white"},
        "heatmap_layer_id": "1-high",
        "overlay_opacity": 1.0,
        "main": {"bbox": [0, 0, 512, 384], "mode": "overlay", "label": "A", "scalebar_um": None},
        "patches": [],
    }

    response = client.post("/api/render-figure", json=spec)

    assert response.status_code == 200
    with Image.open(BytesIO(response.content)).convert("RGB") as image:
        red, _, blue = image.getpixel((80 + 1120, 80 + 490))
    assert red > blue


def test_server_render_figure_overlay_without_heatmap_returns_400(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=15)
    app = create_app(slide_path, reader="image")
    client = TestClient(app)
    spec = {
        "slide_id": 0,
        "canvas": {"width": 2400, "height": 1800, "background": "white"},
        "heatmap_layer_id": "",
        "overlay_opacity": 0.45,
        "main": {"bbox": [64, 48, 448, 336], "mode": "overlay", "label": "A", "scalebar_um": None},
        "patches": [],
    }

    response = client.post("/api/render-figure", json=spec)

    assert response.status_code == 400
    assert "overlay mode requires" in response.json()["detail"]


def test_server_tile_cache_records_hits_misses_and_evictions(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=11)
    app = create_app(slide_path, reader="image", tile_size=128, tile_cache_size=2)
    client = TestClient(app)

    page = client.get("/")
    cache_key = _viewer_config(page.text)["tileCacheKey"]

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
    cache_key = _viewer_config(page.text)["tileCacheKey"]
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
    assert re.fullmatch(r"[0-9a-f]+", _viewer_config(page.text)["tileCacheKey"])
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


def test_server_multiple_raster_heatmap_layers(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=18)
    low_path = tmp_path / "low.png"
    high_path = tmp_path / "high.png"
    Image.new("RGB", (64, 48), (20, 80, 240)).save(low_path)
    Image.new("RGB", (64, 48), (240, 80, 20)).save(high_path)
    app = create_app(
        slide_path,
        raster_heatmap_path=low_path,
        raster_heatmap_layers=[{"name": "high", "path": str(high_path)}],
        reader="image",
    )
    client = TestClient(app)

    payload = client.get("/api/raster-heatmaps").json()
    assert payload["available"] is True
    assert payload["count"] == 2
    assert [layer["name"] for layer in payload["layers"]] == ["low", "high"]
    assert payload["layers"][0]["url"].endswith("/raster_heatmaps/0-low.png")
    assert payload["layers"][1]["url"].endswith("/raster_heatmaps/1-high.png")

    first = client.get("/api/raster-heatmap").json()
    assert first["url"].endswith("/raster_heatmap.png")
    assert first["count"] == 2
    for layer in payload["layers"]:
        response = client.get(layer["url"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.headers["cache-control"] == "public, max-age=3600"


def test_server_raster_heatmap_resize_warning_is_layer_scoped(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=19)
    heatmap_path = tmp_path / "large.png"
    Image.new("RGB", (64, 48), (240, 80, 20)).save(heatmap_path)
    app = create_app(
        slide_path,
        raster_heatmap_path=heatmap_path,
        reader="image",
        max_raster_heatmap_size=16,
    )
    client = TestClient(app)

    payload = client.get("/api/raster-heatmaps").json()
    assert payload["warnings"] == ["raster_heatmap_resized:64x48:16x12"]

    page = client.get("/").text
    visible_html = re.sub(r"<script.*?</script>", "", page, flags=re.DOTALL)
    visible_html = re.sub(r"<style.*?</style>", "", visible_html, flags=re.DOTALL)
    assert "raster_heatmap_resized:64x48:16x12" not in visible_html
    viewer_js, _, _ = _viewer_static_text(client)
    assert "humanizeRasterHeatmapWarning" in viewer_js
    assert "resized ${resizeMatch[1]} -> ${resizeMatch[2]}" in viewer_js


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
    assert "score-threshold-slider" in page.text
    assert "top-k-input" in page.text
    assert "annotation-label-filter" in page.text
    assert "overlay-detail" in page.text
    assert "data-i18n=\"slideMetadata\"" in page.text
    viewer_js, viewer_css, _ = _viewer_static_text(client)
    assert "zoomToImageScale" in viewer_js
    assert "filteredPatches" in viewer_js
    assert "filteredAnnotations" in viewer_js
    assert "zoomToBbox" in viewer_js
    assert "flex-direction: column" in viewer_css
    assert "overflow-y: auto" in viewer_css
    assert "syncLibraryListHeight" not in viewer_js
    assert "setupSlideListScroll" not in viewer_js

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
