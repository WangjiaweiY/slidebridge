from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image

from slidebridge.utils.image import ensure_rgb

try:  # optional dependency
    import tiffslide
except Exception as exc:  # pragma: no cover - depends on local environment
    tiffslide = None  # type: ignore[assignment]
    _TIFFSLIDE_IMPORT_ERROR = exc
else:
    _TIFFSLIDE_IMPORT_ERROR = None


class TiffSlideReader:
    name = "tiffslide"
    priority = 100

    def can_open(self, path: str | Path) -> bool:
        if tiffslide is None:
            raise RuntimeError(f"tiffslide is not available: {_TIFFSLIDE_IMPORT_ERROR}")
        return Path(path).suffix.lower() in {
            ".svs",
            ".tif",
            ".tiff",
            ".ndpi",
            ".mrxs",
            ".scn",
            ".svslide",
        }

    def open(self, path: str | Path) -> "TiffSlideSlide":
        if tiffslide is None:
            raise RuntimeError(f"tiffslide is not available: {_TIFFSLIDE_IMPORT_ERROR}")
        try:
            return TiffSlideSlide(Path(path))
        except Exception as exc:
            raise RuntimeError(f"failed to open with tiffslide: {exc}") from exc


class TiffSlideSlide:
    reader_name = "tiffslide"

    def __init__(self, path: Path) -> None:
        self.path = path
        self._slide = tiffslide.TiffSlide(str(path))
        self.dimensions = _tuple_int(self._slide.dimensions)
        self.level_dimensions = [_tuple_int(item) for item in self._slide.level_dimensions]
        self.level_count = len(self.level_dimensions)
        self.level_downsamples = [float(item) for item in self._slide.level_downsamples]
        self.properties = dict(getattr(self._slide, "properties", {}) or {})
        self.mpp = (
            _first_float(self.properties, ["openslide.mpp-x", "tiffslide.mpp-x", "aperio.MPP"]),
            _first_float(self.properties, ["openslide.mpp-y", "tiffslide.mpp-y", "aperio.MPP"]),
        )
        self.objective_power = _first_float(
            self.properties,
            ["openslide.objective-power", "tiffslide.objective-power", "aperio.AppMag"],
        )
        self.vendor = _first_str(
            self.properties,
            ["openslide.vendor", "tiffslide.vendor", "aperio.ScanScope ID"],
        )
        self.metadata: dict[str, Any] = {
            "mpp": self.mpp,
            "objective_power": self.objective_power,
            "vendor": self.vendor,
        }

    def read_region(
        self, x: int, y: int, width: int, height: int, level: int = 0
    ) -> Image.Image:
        image = self._slide.read_region((int(x), int(y)), int(level), (int(width), int(height)))
        return ensure_rgb(image)

    def get_thumbnail(self, max_size: int = 1024) -> Image.Image:
        image = self._slide.get_thumbnail((int(max_size), int(max_size)))
        return ensure_rgb(image)

    def get_best_level_for_downsample(self, downsample: float) -> int:
        if hasattr(self._slide, "get_best_level_for_downsample"):
            return int(self._slide.get_best_level_for_downsample(float(downsample)))
        return _closest_downsample_level(self.level_downsamples, downsample)

    def close(self) -> None:
        close = getattr(self._slide, "close", None)
        if callable(close):
            close()


def _tuple_int(value: Any) -> tuple[int, int]:
    return int(value[0]), int(value[1])


def _first_float(properties: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = properties.get(key)
        if value is None or value == "":
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            return number
    return None


def _first_str(properties: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = properties.get(key)
        if value:
            return str(value)
    return None


def _closest_downsample_level(downsamples: list[float], downsample: float) -> int:
    if not downsamples:
        return 0
    return min(range(len(downsamples)), key=lambda idx: abs(downsamples[idx] - downsample))
