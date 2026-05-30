from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from slidebridge.utils.paths import ensure_parent


def create_demo_slide(
    out_path: str | Path,
    width: int = 4096,
    height: int = 3072,
    seed: int = 42,
) -> Path:
    width = max(256, int(width))
    height = max(256, int(height))
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    base = np.zeros((height, width, 3), dtype=np.uint8)
    base[:, :] = np.array([248, 232, 238], dtype=np.uint8)
    noise = np_rng.normal(0, 5, size=base.shape)
    base = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(base, mode="RGB").convert("RGBA")

    tissue = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tissue, "RGBA")
    for _ in range(28):
        cx = rng.randint(width // 10, width * 9 // 10)
        cy = rng.randint(height // 10, height * 9 // 10)
        rx = rng.randint(width // 18, width // 5)
        ry = rng.randint(height // 18, height // 5)
        color = rng.choice(
            [
                (230, 142, 174, 58),
                (221, 122, 165, 50),
                (238, 169, 190, 66),
                (216, 150, 184, 54),
            ]
        )
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=color)
    tissue = tissue.filter(ImageFilter.GaussianBlur(radius=18))
    image = Image.alpha_composite(image, tissue)

    draw = ImageDraw.Draw(image, "RGBA")
    for _ in range(max(600, (width * height) // 5500)):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        r = rng.randint(2, 7)
        color = rng.choice(
            [
                (82, 45, 126, 125),
                (102, 54, 138, 115),
                (126, 64, 146, 105),
                (158, 75, 138, 90),
            ]
        )
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)

    for _ in range(120):
        x0 = rng.randint(0, width - 1)
        y0 = rng.randint(0, height - 1)
        x1 = min(width, x0 + rng.randint(width // 30, width // 8))
        y1 = min(height, y0 + rng.randint(8, 32))
        draw.ellipse((x0, y0, x1, y1), fill=(191, 96, 142, 32))

    output = ensure_parent(out_path)
    image.convert("RGB").save(output, format="PNG")
    return output

