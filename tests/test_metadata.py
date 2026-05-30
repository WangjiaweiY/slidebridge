from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from slidebridge.core.metadata import summary


class FakeSlide:
    path = Path("fake.svs")
    reader_name = "fake"
    dimensions = (1000, 500)
    level_count = 2
    level_dimensions = [(1000, 500), (200, 120)]
    level_downsamples = [1.0, 4.0]
    properties: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    mpp = (0.25, 0.27)
    objective_power = 40.0
    vendor = "fake-vendor"

    def read_region(self, x: int, y: int, width: int, height: int, level: int = 0) -> Image.Image:
        return Image.new("RGB", (width, height))

    def get_thumbnail(self, max_size: int = 1024) -> Image.Image:
        return Image.new("RGB", (64, 64))

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 0

    def close(self) -> None:
        return None


def test_summary_includes_metadata_and_warnings():
    info = summary(FakeSlide())

    assert info["filename"] == "fake.svs"
    assert info["reader"] == "fake"
    assert info["width"] == 1000
    assert info["height"] == 500
    assert info["has_mpp"] is True
    assert "mpp_x_y_mismatch" in info["warnings"]
    assert "irregular_level_downsample" in info["warnings"]


def test_summary_missing_mpp_warning():
    slide = FakeSlide()
    slide.mpp = (None, None)

    info = summary(slide)

    assert info["has_mpp"] is False
    assert "missing_mpp" in info["warnings"]
