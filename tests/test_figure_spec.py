from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from slidebridge.readers.image_reader import ImageReader
from slidebridge.render.figure_spec import FIGURE_CANVAS, MAIN_PANEL, PATCH_GRID_COLUMNS, normalize_figure_spec, render_figure_spec_to_image
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
            "fit": "cover",
            "label": "A",
        },
        "patches": [
            {"slot": 0, "bbox": [90, 70, 180, 140], "mode": "raw", "label": "B"},
            {"slot": 1, "bbox": [210, 120, 300, 210], "mode": "overlay", "label": "C"},
            {"slot": 2, "bbox": [320, 160, 400, 240], "mode": "raw", "label": "D"},
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
    main_panel = summary["main"]["panel"]
    assert main_panel[2] <= MAIN_PANEL[2]
    assert main_panel[3] <= MAIN_PANEL[3]
    assert main_panel[2] % PATCH_GRID_COLUMNS == 0
    assert summary["main"]["scalebar_drawn"] is True
    assert len(summary["patches"]) == 3
    assert summary["patches"][0]["mode"] == "raw"
    assert summary["patches"][1]["mode"] == "overlay"
    patch_size = main_panel[2] // PATCH_GRID_COLUMNS
    assert summary["patches"][0]["panel"][2:] == [patch_size, patch_size]
    assert summary["patches"][0]["panel"][0] == main_panel[0]
    assert summary["patches"][1]["panel"][0] == summary["patches"][0]["panel"][0] + patch_size
    assert summary["patches"][2]["panel"][0] == summary["patches"][1]["panel"][0] + patch_size
    assert summary["patches"][PATCH_GRID_COLUMNS - 1]["panel"][0] + patch_size == main_panel[0] + main_panel[2]


def test_figure_spec_keeps_main_bbox_and_squares_patch_bboxes(tmp_path):
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
    assert main == [40, 40, 360, 180]
    patch = normalized["patches"][0]["bbox"]
    assert patch[2] - patch[0] == patch[3] - patch[1]


def test_figure_spec_main_contain_keeps_full_slide_bbox(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=55)
    heatmap_path = _demo_heatmap(tmp_path / "heatmap.png")
    slide = ImageReader().open(slide_path)
    spec = _figure_spec()
    spec["show_labels"] = False
    spec["main"] = {"bbox": [0, 0, 512, 384], "mode": "overlay", "fit": "contain", "label": "A"}
    spec["patches"] = []

    try:
        image, summary = render_figure_spec_to_image(slide, spec, raster_heatmap_paths={"0-low": heatmap_path})
    finally:
        slide.close()

    assert image.size == FIGURE_CANVAS
    assert summary["show_labels"] is False
    assert summary["main"]["bbox"] == [0, 0, 512, 384]
    assert summary["main"]["fit"] == "contain"
    main_panel = summary["main"]["panel"]
    assert summary["main"]["view"]["content_box"] == [0, 0, main_panel[2], main_panel[3]]
    assert main_panel[2] / main_panel[3] == pytest.approx(512 / 384, rel=0.01)


def test_figure_spec_patch_grid_uses_main_content_width(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=56)
    heatmap_path = _demo_heatmap(tmp_path / "heatmap.png")
    slide = ImageReader().open(slide_path)
    spec = _figure_spec()
    spec["main"] = {"bbox": [0, 0, 512, 384], "mode": "overlay", "fit": "contain", "label": "A"}
    spec["patches"] = [
        {"slot": slot, "bbox": [64, 64, 160, 160], "mode": "raw", "label": chr(ord("B") + slot)}
        for slot in range(6)
    ]

    try:
        _, summary = render_figure_spec_to_image(slide, spec, raster_heatmap_paths={"0-low": heatmap_path})
    finally:
        slide.close()

    main_panel = summary["main"]["panel"]
    patch_size = main_panel[2] // PATCH_GRID_COLUMNS
    patches = {patch["slot"]: patch["panel"] for patch in summary["patches"]}

    assert main_panel[2] == patch_size * PATCH_GRID_COLUMNS
    for slot in range(6):
        assert patches[slot][2:] == [patch_size, patch_size]
    assert patches[0][0] == main_panel[0]
    assert patches[1][0] == patches[0][0] + patch_size
    assert patches[2][0] == patches[1][0] + patch_size
    assert patches[2][0] + patch_size == main_panel[0] + main_panel[2]
    assert patches[3][0] == main_panel[0]
    assert patches[5][0] + patch_size == main_panel[0] + main_panel[2]


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
