from __future__ import annotations

import numpy as np
from PIL import Image

from slidebridge.annotations.table import AnnotationRecord, AnnotationTable
from slidebridge.overlays.patch_table import PatchRecord, PatchTable
from slidebridge.readers.image_reader import ImageReader
from slidebridge.render.view import render_view, render_view_to_image
from slidebridge.utils.demo import create_demo_slide


class _PyramidSlide:
    path = None
    reader_name = "fake"
    dimensions = (4096, 3072)
    level_count = 3
    level_dimensions = [(4096, 3072), (1024, 768), (256, 192)]
    level_downsamples = [1.0, 4.0, 16.0]
    properties = {}
    metadata = {}
    mpp = (None, None)
    objective_power = None
    vendor = None

    def __init__(self):
        self.calls = []

    def read_region(self, x: int, y: int, width: int, height: int, level: int = 0) -> Image.Image:
        self.calls.append((x, y, width, height, level))
        return Image.new("RGB", (width, height), (230, 230, 230))

    def get_thumbnail(self, max_size: int = 1024) -> Image.Image:
        return Image.new("RGB", (max_size, max_size), (230, 230, 230))

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 2 if downsample >= 12 else 1 if downsample >= 3 else 0

    def close(self) -> None:
        pass


def test_render_view_with_patches_annotations_and_raster_heatmap(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=21)
    heatmap_path = tmp_path / "heatmap.png"
    Image.fromarray(np.tile(np.arange(64, dtype=np.uint8), (48, 1)) * 4).save(heatmap_path)
    slide = ImageReader().open(slide_path)
    patch_table = PatchTable(
        [
            PatchRecord(200, 150, 64, 64, score=0.8, index=0),
            PatchRecord(10, 10, 32, 32, score=0.2, index=1),
        ]
    )
    annotation_table = AnnotationTable(
        [
            AnnotationRecord(
                id="rect-1",
                type="rectangle",
                coordinates={"x": 220, "y": 160, "width": 80, "height": 60},
                label="Synthetic",
                color="#00aa88",
            )
        ]
    )
    out = tmp_path / "view.png"

    try:
        result = render_view(
            slide,
            out,
            patch_table=patch_table,
            annotation_table=annotation_table,
            center_x=256,
            center_y=192,
            window_width=256,
            window_height=192,
            out_width=320,
            out_height=240,
            raster_heatmap_path=heatmap_path,
        )
    finally:
        slide.close()

    assert result["view_bbox"] == [128, 96, 384, 288]
    assert result["rendered_patches_count"] == 1
    assert result["rendered_annotations_count"] == 1
    assert result["raster_heatmap"]["available"] is True
    with Image.open(out) as rendered:
        assert rendered.mode == "RGB"
        assert rendered.size == (320, 240)


def test_render_view_scale_controls_output_window(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=22)
    slide = ImageReader().open(slide_path)

    try:
        result = render_view(
            slide,
            tmp_path / "scaled.png",
            center_x=256,
            center_y=192,
            out_width=200,
            out_height=100,
            scale=1.0,
        )
    finally:
        slide.close()

    assert result["window_width"] == 200
    assert result["window_height"] == 100
    assert result["scale"] == 1.0


def test_render_view_to_image_returns_image_and_summary(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=24)
    slide = ImageReader().open(slide_path)

    try:
        image, result = render_view_to_image(
            slide,
            center_x=256,
            center_y=192,
            window_width=256,
            window_height=192,
            out_width=320,
            out_height=240,
        )
    finally:
        slide.close()

    assert image.mode == "RGB"
    assert image.size == (320, 240)
    assert result["output_path"] is None
    assert result["view_bbox"] == [128, 96, 384, 288]
    assert result["window_width"] == 256
    assert result["window_height"] == 192


def test_render_view_to_image_uses_pyramid_level_for_downsampled_view():
    slide = _PyramidSlide()

    image, result = render_view_to_image(
        slide,
        center_x=2048,
        center_y=1536,
        window_width=4096,
        window_height=3072,
        out_width=512,
        out_height=384,
    )

    assert image.size == (512, 384)
    assert slide.calls[0] == (0, 0, 1024, 768, 1)
    assert result["read_level"] == 1
    assert result["read_level_downsample"] == 4.0


def test_render_view_rejects_scale_and_magnification_together(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=192, seed=23)
    slide = ImageReader().open(slide_path)

    try:
        try:
            render_view(slide, tmp_path / "bad.png", scale=1.0, magnification=10.0)
        except ValueError as exc:
            assert "either" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("Expected conflicting scale and magnification to raise")
    finally:
        slide.close()
