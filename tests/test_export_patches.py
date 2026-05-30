from __future__ import annotations

import csv

from PIL import Image

from slidebridge.export.patches import export_patches
from slidebridge.overlays.patch_table import PatchRecord, PatchTable
from slidebridge.readers.image_reader import ImageReader


def test_export_patches_jpg_and_manifest(tmp_path):
    slide_path = tmp_path / "slide.png"
    Image.new("RGB", (128, 128), (200, 100, 150)).save(slide_path)
    slide = ImageReader().open(slide_path)
    table = PatchTable([PatchRecord(0, 0, 32, 32, score=0.5)])

    result = export_patches(slide, table, tmp_path / "patches", image_format="jpg")

    assert result["exported"] == 1
    assert (tmp_path / "patches" / "manifest.csv").exists()
    assert len(list((tmp_path / "patches").glob("*.jpg"))) == 1
    slide.close()


def test_export_patches_png_limit(tmp_path):
    slide_path = tmp_path / "slide.png"
    Image.new("RGB", (128, 128), (200, 100, 150)).save(slide_path)
    slide = ImageReader().open(slide_path)
    table = PatchTable([PatchRecord(0, 0, 32, 32), PatchRecord(32, 32, 32, 32)])

    result = export_patches(slide, table, tmp_path / "patches", image_format="png", limit=1)

    assert result["exported"] == 1
    assert len(list((tmp_path / "patches").glob("*.png"))) == 1
    slide.close()


def test_export_patches_out_of_bounds_does_not_crash(tmp_path):
    slide_path = tmp_path / "slide.png"
    Image.new("RGB", (128, 128), (200, 100, 150)).save(slide_path)
    slide = ImageReader().open(slide_path)
    table = PatchTable([PatchRecord(120, 120, 32, 32), PatchRecord(200, 200, 32, 32)])

    result = export_patches(slide, table, tmp_path / "patches")

    assert result["exported"] == 1
    assert result["skipped"] == 1
    with (tmp_path / "patches" / "manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["width"] == "8"
    assert rows[0]["height"] == "8"
    slide.close()

