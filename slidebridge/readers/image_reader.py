from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from slidebridge.utils.image import ensure_rgb
from slidebridge.utils.paths import SUPPORTED_IMAGE_EXTENSIONS


class ImageReader:
    name = "image"
    priority = 10

    def can_open(self, path: str | Path) -> bool:
        image_path = Path(path)
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            return False
        try:
            with Image.open(image_path) as image:
                image.verify()
            return True
        except Exception:
            return False

    def open(self, path: str | Path) -> "ImageSlide":
        try:
            return ImageSlide(Path(path))
        except Exception as exc:
            raise RuntimeError(f"failed to open with Pillow: {exc}") from exc


class ImageSlide:
    reader_name = "image"

    def __init__(self, path: Path) -> None:
        self.path = path
        with Image.open(path) as image:
            self._image = ensure_rgb(image).copy()
        self.dimensions = (int(self._image.width), int(self._image.height))
        self.level_count = 1
        self.level_dimensions = [self.dimensions]
        self.level_downsamples = [1.0]
        self.properties: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}
        self.mpp = (None, None)
        self.objective_power = None
        self.vendor = None

    def read_region(
        self, x: int, y: int, width: int, height: int, level: int = 0
    ) -> Image.Image:
        if level != 0:
            raise ValueError("ImageReader only supports level 0")
        x = int(x)
        y = int(y)
        width = max(1, int(width))
        height = max(1, int(height))

        output = Image.new("RGB", (width, height), (255, 255, 255))
        left = max(0, x)
        top = max(0, y)
        right = min(self._image.width, x + width)
        bottom = min(self._image.height, y + height)
        if right <= left or bottom <= top:
            return output

        crop = self._image.crop((left, top, right, bottom))
        output.paste(crop, (left - x, top - y))
        return output

    def get_thumbnail(self, max_size: int = 1024) -> Image.Image:
        image = self._image.copy()
        image.thumbnail((int(max_size), int(max_size)), Image.Resampling.LANCZOS)
        return ensure_rgb(image)

    def get_best_level_for_downsample(self, downsample: float) -> int:
        return 0

    def close(self) -> None:
        self._image.close()
