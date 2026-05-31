from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

RASTER_HEATMAP_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass
class RasterHeatmap:
    path: Path
    image: Image.Image
    source_size: tuple[int, int]
    mode: str
    warnings: list[str]

    def to_png_bytes(self) -> bytes:
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        return buffer.getvalue()

    def summary(self, slide_width: int | None = None, slide_height: int | None = None) -> dict[str, Any]:
        warnings = list(self.warnings)
        if slide_width and slide_height:
            slide_ratio = float(slide_width) / float(slide_height)
            heatmap_ratio = float(self.source_size[0]) / float(self.source_size[1])
            if abs(slide_ratio - heatmap_ratio) / max(slide_ratio, 1e-12) > 0.02:
                warnings.append("raster_heatmap_aspect_ratio_mismatch")
        return {
            "available": True,
            "source": str(self.path),
            "source_width": self.source_size[0],
            "source_height": self.source_size[1],
            "served_width": self.image.width,
            "served_height": self.image.height,
            "mode": self.mode,
            "coordinate_space": "level0",
            "mapping": "stretch_to_full_slide",
            "warnings": warnings,
        }


def is_raster_heatmap_path(path: str | Path | None) -> bool:
    if path is None:
        return False
    return Path(str(path)).suffix.lower() in RASTER_HEATMAP_EXTENSIONS


def load_raster_heatmap(path: str | Path, max_size: int = 4096) -> RasterHeatmap:
    heatmap_path = Path(path)
    if heatmap_path.suffix.lower() not in RASTER_HEATMAP_EXTENSIONS:
        raise ValueError("Raster heatmap must be a PNG, JPG, or JPEG image.")
    warnings: list[str] = []
    with Image.open(heatmap_path) as image:
        source_size = image.size
        mode = "rgb"
        if _is_grayscale(image):
            rgba = _colorize_grayscale(image, warnings)
            mode = "grayscale-colorized"
        else:
            rgba = image.convert("RGBA")
            mode = "rgba" if "A" in image.getbands() else "rgb"
    rgba = _resize_if_needed(rgba, max_size=max_size, warnings=warnings)
    return RasterHeatmap(heatmap_path, rgba, source_size, mode, warnings)


def composite_raster_heatmap(
    base: Image.Image,
    path: str | Path,
    opacity: float = 0.45,
    max_size: int = 4096,
) -> tuple[Image.Image, RasterHeatmap]:
    heatmap = load_raster_heatmap(path, max_size=max_size)
    overlay = heatmap.image.resize(base.size, Image.Resampling.BILINEAR).convert("RGBA")
    alpha = overlay.getchannel("A")
    alpha = alpha.point(lambda value: int(value * max(0.0, min(1.0, float(opacity)))))
    overlay.putalpha(alpha)
    composed = Image.alpha_composite(base.convert("RGBA"), overlay)
    return composed, heatmap


def _is_grayscale(image: Image.Image) -> bool:
    bands = image.getbands()
    return image.mode in {"1", "L", "I", "I;16", "F"} or bands == ("L",) or bands == ("I",)


def _colorize_grayscale(image: Image.Image, warnings: list[str]) -> Image.Image:
    values = np.asarray(image.convert("F"), dtype=np.float32)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        normalized = np.zeros(values.shape, dtype=np.float32)
        warnings.append("raster_heatmap_no_finite_values")
    else:
        vmin = float(finite.min())
        vmax = float(finite.max())
        if vmax <= vmin:
            normalized = np.zeros(values.shape, dtype=np.float32)
            warnings.append("raster_heatmap_constant_values")
        else:
            normalized = (values - vmin) / (vmax - vmin)
            normalized = np.clip(normalized, 0.0, 1.0)
    rgb = _score_colormap(normalized)
    alpha = np.full(normalized.shape, 255, dtype=np.uint8)
    rgba = np.dstack([rgb, alpha])
    return Image.fromarray(rgba)


def _score_colormap(values: np.ndarray) -> np.ndarray:
    values = np.clip(values.astype(np.float32), 0.0, 1.0)
    rgb = np.zeros((*values.shape, 3), dtype=np.uint8)
    low = values < 0.5
    high = ~low
    t_low = np.zeros_like(values)
    t_low[low] = values[low] / 0.5
    rgb[..., 0][low] = np.round(48 + (245 - 48) * t_low[low]).astype(np.uint8)
    rgb[..., 1][low] = np.round(112 + (211 - 112) * t_low[low]).astype(np.uint8)
    rgb[..., 2][low] = np.round(210 + (84 - 210) * t_low[low]).astype(np.uint8)
    t_high = np.zeros_like(values)
    t_high[high] = (values[high] - 0.5) / 0.5
    rgb[..., 0][high] = np.round(245 + (220 - 245) * t_high[high]).astype(np.uint8)
    rgb[..., 1][high] = np.round(211 + (48 - 211) * t_high[high]).astype(np.uint8)
    rgb[..., 2][high] = np.round(84 + (48 - 84) * t_high[high]).astype(np.uint8)
    return rgb


def _resize_if_needed(image: Image.Image, max_size: int, warnings: list[str]) -> Image.Image:
    max_size = max(1, int(max_size))
    longest = max(image.size)
    if longest <= max_size:
        return image
    scale = max_size / float(longest)
    new_size = (max(1, int(round(image.width * scale))), max(1, int(round(image.height * scale))))
    warnings.append(f"raster_heatmap_resized:{image.width}x{image.height}:{new_size[0]}x{new_size[1]}")
    return image.resize(new_size, Image.Resampling.BILINEAR)
