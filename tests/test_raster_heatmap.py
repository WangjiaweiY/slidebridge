from __future__ import annotations

import numpy as np
from PIL import Image

from slidebridge.core.registry import open_slide
from slidebridge.overlays.raster_heatmap import is_raster_heatmap_path, load_raster_heatmap
from slidebridge.render.overlay import render_overlay
from slidebridge.utils.demo import create_demo_slide


def test_is_raster_heatmap_path():
    assert is_raster_heatmap_path("heatmap.png") is True
    assert is_raster_heatmap_path("heatmap.jpg") is True
    assert is_raster_heatmap_path("heatmap.jpeg") is True
    assert is_raster_heatmap_path("scores.npy") is False


def test_load_grayscale_raster_heatmap_colorizes(tmp_path):
    data = np.linspace(0, 255, 100, dtype=np.uint8).reshape(10, 10)
    path = tmp_path / "heatmap.png"
    Image.fromarray(data).save(path)

    heatmap = load_raster_heatmap(path)

    assert heatmap.image.mode == "RGBA"
    assert heatmap.image.size == (10, 10)
    assert heatmap.mode == "grayscale-colorized"
    assert heatmap.to_png_bytes().startswith(b"\x89PNG")


def test_load_rgb_raster_heatmap_preserves_rgb_mode(tmp_path):
    path = tmp_path / "heatmap.jpg"
    Image.new("RGB", (12, 8), (255, 32, 16)).save(path)

    heatmap = load_raster_heatmap(path)

    assert heatmap.image.mode == "RGBA"
    assert heatmap.source_size == (12, 8)
    assert heatmap.mode == "rgb"


def test_render_overlay_with_raster_heatmap_only(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=9)
    heatmap_path = tmp_path / "raster_heatmap.png"
    Image.fromarray(np.tile(np.arange(64, dtype=np.uint8), (48, 1)) * 4).save(heatmap_path)
    slide = open_slide(slide_path, reader="image")
    try:
        out = tmp_path / "overlay.png"
        result = render_overlay(slide, None, out, raster_heatmap_path=heatmap_path)
    finally:
        slide.close()

    assert out.exists()
    assert result["raster_heatmap"]["available"] is True
    assert result["rendered_patches_count"] == 0
    with Image.open(out) as rendered:
        assert rendered.size[0] > 0
