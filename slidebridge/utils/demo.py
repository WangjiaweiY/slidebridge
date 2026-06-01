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


def create_demo_heatmap(
    out_path: str | Path,
    width: int = 1024,
    height: int = 768,
    seed: int = 42,
    style: str = "hotspot",
) -> Path:
    width = max(64, int(width))
    height = max(64, int(height))
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    x = xx.astype(np.float32) / max(1, width - 1)
    y = yy.astype(np.float32) / max(1, height - 1)
    style = str(style or "hotspot").lower()
    if style == "gradient":
        values = 0.15 + 0.8 * x
    elif style == "rings":
        radius = np.sqrt((x - 0.52) ** 2 + (y - 0.48) ** 2)
        values = 0.5 + 0.5 * np.sin(radius * 32.0)
        values *= np.clip(1.1 - radius * 1.5, 0.0, 1.0)
    elif style == "hotspot":
        centers = [(0.30, 0.35, 0.95), (0.56, 0.50, 1.0), (0.76, 0.62, 0.85)]
        values = np.zeros((height, width), dtype=np.float32)
        for cx, cy, amp in centers:
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            values = np.maximum(values, amp * np.exp(-d2 / (2 * 0.0105)))
    else:
        raise ValueError("Demo heatmap style must be one of: hotspot, gradient, rings")
    values = values + rng.normal(0.0, 0.025, size=values.shape)
    values = np.clip(values, 0.0, 1.0)
    image = Image.fromarray(_heatmap_colormap(values))
    output = ensure_parent(out_path)
    fmt = "JPEG" if output.suffix.lower() in {".jpg", ".jpeg"} else "PNG"
    image.save(output, format=fmt, quality=92)
    return output


def _heatmap_colormap(values: np.ndarray) -> np.ndarray:
    values = np.clip(values.astype(np.float32), 0.0, 1.0)
    rgb = np.zeros((*values.shape, 3), dtype=np.uint8)
    low = values < 0.5
    high = ~low
    low_t = np.zeros_like(values)
    low_t[low] = values[low] / 0.5
    rgb[..., 0][low] = np.round(48 + (245 - 48) * low_t[low]).astype(np.uint8)
    rgb[..., 1][low] = np.round(112 + (211 - 112) * low_t[low]).astype(np.uint8)
    rgb[..., 2][low] = np.round(210 + (84 - 210) * low_t[low]).astype(np.uint8)
    high_t = np.zeros_like(values)
    high_t[high] = (values[high] - 0.5) / 0.5
    rgb[..., 0][high] = np.round(245 + (220 - 245) * high_t[high]).astype(np.uint8)
    rgb[..., 1][high] = np.round(211 + (48 - 211) * high_t[high]).astype(np.uint8)
    rgb[..., 2][high] = np.round(84 + (48 - 84) * high_t[high]).astype(np.uint8)
    return rgb
