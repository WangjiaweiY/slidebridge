from __future__ import annotations

from PIL import Image

from slidebridge.readers.image_reader import ImageReader


def test_image_reader_dimensions(tmp_path):
    path = tmp_path / "image.png"
    Image.new("RGB", (100, 80), (255, 255, 255)).save(path)

    slide = ImageReader().open(path)

    assert slide.dimensions == (100, 80)
    assert slide.level_count == 1
    slide.close()


def test_image_reader_read_region(tmp_path):
    path = tmp_path / "image.png"
    Image.new("RGB", (100, 80), (255, 255, 255)).save(path)

    slide = ImageReader().open(path)
    region = slide.read_region(10, 20, 30, 40)

    assert region.size == (30, 40)
    assert region.mode == "RGB"
    slide.close()


def test_image_reader_thumbnail(tmp_path):
    path = tmp_path / "image.png"
    Image.new("RGB", (200, 100), (255, 255, 255)).save(path)

    slide = ImageReader().open(path)
    thumbnail = slide.get_thumbnail(max_size=50)

    assert thumbnail.size[0] <= 50
    assert thumbnail.size[1] <= 50
    assert thumbnail.mode == "RGB"
    slide.close()

