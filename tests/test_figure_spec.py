from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from slidebridge.readers.image_reader import ImageReader
from slidebridge.render.figure_spec import FIGURE_CANVAS, MAIN_PANEL, PATCH_SLOT_SIZE, normalize_figure_spec, render_figure_spec_to_image
from slidebridge.utils.demo import create_demo_slide


def _demo_heatmap(path):
    data = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (48, 1))
    Image.fromarray(data, mode="L").save(path)
    return path


def _figure_spec(layer_id: str = "0-low", main_mode: str = "overlay") -> dict:
    return {
        "slide_id": 0,
        "canvas": {"width": 2400, "height": 1800, "background": "white"},
        "heatmap_layer_id": layer_id,
        "overlay_opacity": 0.5,
        "main": {
            "bbox": [64, 48, 448, 336],
            "mode": main_mode,
            "label": "A",
        },
        "patches": [
            {"slot": 0, "bbox": [90, 70, 180, 140], "mode": "raw", "label": "B"},
            {"slot": 1, "bbox": [210, 120, 300, 210], "mode": "overlay", "label": "C"},
        ],
    }


def test_render_figure_spec_with_raw_and_overlay_slots(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=51)
    heatmap_path = _demo_heatmap(tmp_path / "heatmap.png")
    slide = ImageReader().open(slide_path)
    slide.mpp = (0.5, 0.5)
    spec = _figure_spec()
    spec["main"]["scalebar_um"] = 100

    try:
        image, summary = render_figure_spec_to_image(slide, spec, raster_heatmap_paths={"0-low": heatmap_path})
    finally:
        slide.close()

    assert image.mode == "RGB"
    assert image.size == FIGURE_CANVAS
    assert summary["main"]["panel"] == list(MAIN_PANEL)
    assert summary["main"]["scalebar_drawn"] is True
    assert len(summary["patches"]) == 2
    assert summary["patches"][0]["mode"] == "raw"
    assert summary["patches"][1]["mode"] == "overlay"
    assert summary["patches"][0]["panel"][2:] == [PATCH_SLOT_SIZE, PATCH_SLOT_SIZE]


def test_figure_spec_adjusts_bboxes_to_panel_aspect(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=52)
    heatmap_path = _demo_heatmap(tmp_path / "heatmap.png")
    slide = ImageReader().open(slide_path)
    spec = _figure_spec()
    spec["main"]["bbox"] = [40, 40, 360, 180]
    spec["main"]["mode"] = "raw"
    spec["patches"] = [{"slot": 0, "bbox": [90, 70, 180, 140], "mode": "raw", "label": "B"}]

    try:
        normalized = normalize_figure_spec(slide=slide, spec=spec, raster_heatmap_paths={"0-low": heatmap_path})
    finally:
        slide.close()

    main = normalized["main"]["bbox"]
    main_ratio = (main[2] - main[0]) / (main[3] - main[1])
    assert main_ratio == pytest.approx(MAIN_PANEL[2] / MAIN_PANEL[3], rel=0.03)
    patch = normalized["patches"][0]["bbox"]
    assert patch[2] - patch[0] == patch[3] - patch[1]


def test_figure_spec_overlay_requires_heatmap_layer(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=53)
    slide = ImageReader().open(slide_path)

    try:
        with pytest.raises(ValueError, match="overlay mode requires"):
            render_figure_spec_to_image(slide, _figure_spec(), raster_heatmap_paths={})
    finally:
        slide.close()


def test_figure_spec_scalebar_requires_mpp(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=54)
    heatmap_path = _demo_heatmap(tmp_path / "heatmap.png")
    slide = ImageReader().open(slide_path)
    spec = _figure_spec()
    spec["main"]["scalebar_um"] = 100

    try:
        with pytest.raises(ValueError, match="requires slide mpp metadata"):
            render_figure_spec_to_image(slide, spec, raster_heatmap_paths={"0-low": heatmap_path})
    finally:
        slide.close()
