from __future__ import annotations

from PIL import Image

from slidebridge.qc.blur import blur_score
from slidebridge.qc.tissue import estimate_tissue_percent


def test_estimate_tissue_percent_returns_percent_range():
    image = Image.new("RGB", (64, 64), (180, 80, 130))

    value = estimate_tissue_percent(image)

    assert 0.0 <= value <= 100.0


def test_blur_score_returns_float():
    image = Image.new("RGB", (64, 64), (255, 255, 255))

    value = blur_score(image)

    assert isinstance(value, float)
    assert value >= 0.0

