from __future__ import annotations

import numpy as np
from PIL import Image

from slidebridge.readers.image_reader import ImageReader
from slidebridge.render.figure import render_figure, render_figure_to_image
from slidebridge.utils.demo import create_demo_slide


def _demo_heatmap(path):
    gradient = np.linspace(0, 255, 128, dtype=np.uint8)
    image = np.tile(gradient, (96, 1))
    Image.fromarray(image, mode="L").save(path)
    return path


def test_render_figure_with_inset_heatmap_title_and_scalebar(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=31)
    heatmap_path = _demo_heatmap(tmp_path / "heatmap.png")
    out = tmp_path / "figure.png"
    slide = ImageReader().open(slide_path)

    try:
        result = render_figure(
            slide,
            out,
            center_x=256,
            center_y=192,
            window_width=256,
            window_height=192,
            main_width=320,
            raster_heatmap_path=heatmap_path,
            inset_x=180,
            inset_y=120,
            inset_width=96,
            inset_height=96,
            inset_size=128,
            title="Model output overview",
            panel_label="A",
            scalebar_um=100,
            mpp=0.5,
        )
    finally:
        slide.close()

    assert out.exists()
    assert result["figure_size"][0] > 320
    assert result["inset_bbox"] == [180, 120, 276, 216]
    assert len(result["insets"]) == 2
    assert result["scalebar_drawn"] is True
    with Image.open(out) as image:
        assert image.mode == "RGB"
        assert image.width == result["figure_size"][0]
        assert image.height == result["figure_size"][1]


def test_render_figure_to_image_without_inset(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=32)
    slide = ImageReader().open(slide_path)

    try:
        image, result = render_figure_to_image(
            slide,
            center_x=256,
            center_y=192,
            window_width=256,
            window_height=192,
            main_width=320,
            main_height=240,
        )
    finally:
        slide.close()

    assert image.mode == "RGB"
    assert result["inset_bbox"] is None
    assert result["insets"] == []
    assert result["main_view"]["view_bbox"] == [128, 96, 384, 288]


def test_render_figure_requires_both_inset_coordinates(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=192, seed=33)
    slide = ImageReader().open(slide_path)

    try:
        try:
            render_figure_to_image(slide, inset_x=10)
        except ValueError as exc:
            assert "provided together" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("Expected missing inset y coordinate to raise")
    finally:
        slide.close()


def test_render_figure_rejects_out_of_bounds_inset(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=192, seed=34)
    slide = ImageReader().open(slide_path)

    try:
        try:
            render_figure_to_image(slide, inset_x=999, inset_y=999)
        except ValueError as exc:
            assert "outside the slide bounds" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("Expected out-of-bounds inset to raise")
    finally:
        slide.close()


def test_render_figure_scalebar_requires_mpp_for_plain_image(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=192, seed=35)
    slide = ImageReader().open(slide_path)

    try:
        try:
            render_figure_to_image(slide, scalebar_um=100)
        except ValueError as exc:
            assert "--scalebar-um requires slide mpp metadata or --mpp" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("Expected missing mpp to raise")
    finally:
        slide.close()
