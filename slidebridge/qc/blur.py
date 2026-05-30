from __future__ import annotations

import numpy as np
from PIL import Image

from slidebridge.utils.image import resize_max


def blur_score(image: Image.Image) -> float:
    gray = resize_max(image.convert("L"), 1024)
    array = np.asarray(gray, dtype=np.float32)
    if array.shape[0] < 3 or array.shape[1] < 3:
        return 0.0

    center = array[1:-1, 1:-1]
    laplacian = (
        array[:-2, 1:-1]
        + array[2:, 1:-1]
        + array[1:-1, :-2]
        + array[1:-1, 2:]
        - 4.0 * center
    )
    return float(np.var(laplacian))

