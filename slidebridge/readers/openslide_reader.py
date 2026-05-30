from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image

from slidebridge.utils.image import ensure_rgb

try:  # optional dependency
    import openslide
except Exception as exc:  # pragma: no cover - depends on local environment
    openslide = None  # type: ignore[assignment]
    _OPENSLIDE_IMPORT_ERROR = exc
else:
    _OPENSLIDE_IMPORT_ERROR = None


class OpenSlideReader:
    name = "openslide"
    priority = 90

    def can_open(self, path: str | Path) -> bool:
        if openslide is None:
            raise RuntimeError(f"openslide is not available: {_OPENSLIDE_IMPORT_ERROR}")
        return Path(path).suffix.lower() in {
            ".svs",
            ".tif",
            ".tiff",
            ".ndpi",
            ".mrxs",
            ".scn",
            ".svslide",
        }

    def open(self, path: str | Path) -> "OpenSlideSlide":
        if openslide is None:
            raise RuntimeError(f"openslide is not available: {_OPENSLIDE_IMPORT_ERROR}")
        try:
            return OpenSlideSlide(Path(path))
        except Exception as exc:
            raise RuntimeError(f"failed to open with openslide: {exc}") from exc


class OpenSlideSlide:
    reader_name = "openslide"

    def __init__(self, path: Path) -> None:
        self.path = path
        self._slide = openslide.OpenSlide(str(path))
        self.dimensions = _tuple_int(self._slide.dimensions)
        self.level_dimensions = [_tuple_int(item) for item in self._slide.level_dimensions]
        self.level_count = int(self._slide.level_count)
        self.level_downsamples = [float(item) for item in self._slide.level_downsamples]
        self.properties = dict(getattr(self._slide, "properties", {}) or {})
        self.mpp = (
            _as_float(self.properties.get("openslide.mpp-x")),
            _as_float(self.properties.get("openslide.mpp-y")),
        )
        self.objective_power = _as_float(self.properties.get("openslide.objective-power"))
        self.vendor = _as_str(self.properties.get("openslide.vendor"))
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
        return int(self._slide.get_best_level_for_downsample(float(downsample)))

    def close(self) -> None:
        close = getattr(self._slide, "close", None)
        if callable(close):
            close()


def _tuple_int(value: Any) -> tuple[int, int]:
    return int(value[0]), int(value[1])


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _as_str(value: Any) -> str | None:
    return str(value) if value else None
