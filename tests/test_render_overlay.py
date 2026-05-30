from __future__ import annotations

from PIL import Image

from slidebridge.overlays.patch_table import PatchRecord, PatchTable
from slidebridge.readers.image_reader import ImageReader
from slidebridge.render.overlay import render_overlay
from slidebridge.utils.demo import create_demo_slide


def test_render_overlay_with_scores_outputs_png(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=10)
    slide = ImageReader().open(slide_path)
    table = PatchTable(
        [
            PatchRecord(10, 20, 64, 64, score=0.1, index=0),
            PatchRecord(80, 90, 64, 64, score=0.9, index=1),
        ]
    )
    out = tmp_path / "overlay.png"

    result = render_overlay(slide, table, out, max_size=256)

    assert result["rendered_patches_count"] == 2
    assert out.exists()
    with Image.open(out) as image:
        assert image.mode == "RGB"
        assert max(image.size) <= 256
    slide.close()


def test_render_overlay_without_scores_outputs_jpg(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=11)
    slide = ImageReader().open(slide_path)
    table = PatchTable([PatchRecord(10, 20, 64, 64), PatchRecord(80, 90, 64, 64)])
    out = tmp_path / "overlay.jpg"

    result = render_overlay(slide, table, out, max_size=256, image_format="jpg")

    assert result["has_scores"] is False
    assert out.exists()
    with Image.open(out) as image:
        assert image.format == "JPEG"
    slide.close()


def test_render_overlay_skips_outside_patches(tmp_path):
    slide_path = create_demo_slide(tmp_path / "demo.png", width=256, height=256, seed=12)
    slide = ImageReader().open(slide_path)
    table = PatchTable([PatchRecord(9999, 9999, 64, 64), PatchRecord(10, 10, 32, 32)])

    result = render_overlay(slide, table, tmp_path / "overlay.png", max_size=128)

    assert result["rendered_patches_count"] == 1
    slide.close()

