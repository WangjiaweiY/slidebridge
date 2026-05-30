from __future__ import annotations

import numpy as np
from PIL import Image

from slidebridge.utils.image import ensure_rgb, resize_max


def estimate_tissue_percent(thumbnail: Image.Image) -> float:
    image = resize_max(ensure_rgb(thumbnail), 1024)
    array = np.asarray(image, dtype=np.float32)
    if array.size == 0:
        return 0.0

    brightness = array.mean(axis=2)
    saturation = array.max(axis=2) - array.min(axis=2)
    mask = (saturation > 20) & (brightness < 245) & (brightness > 20)
    total = mask.size
    if total == 0:
        return 0.0
    return float(mask.sum() / total * 100.0)

