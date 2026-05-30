from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, Tuple, runtime_checkable

from PIL import Image


@runtime_checkable
class Slide(Protocol):
    """A normalized whole-slide image object.

    Coordinate convention:
    - x/y inputs are always level-0 coordinates.
    - read_region width/height are output pixel sizes at the requested level.
    """

    path: Path
    reader_name: str
    dimensions: Tuple[int, int]
    level_count: int
    level_dimensions: list[tuple[int, int]]
    level_downsamples: list[float]
    properties: dict[str, Any]
    metadata: dict[str, Any]
    mpp: tuple[float | None, float | None]
    objective_power: float | None
    vendor: str | None

    def read_region(
        self, x: int, y: int, width: int, height: int, level: int = 0
    ) -> Image.Image:
        """Read a region using level-0 x/y coordinates."""

    def get_thumbnail(self, max_size: int = 1024) -> Image.Image:
        """Return an RGB thumbnail whose longest side is at most max_size."""

    def get_best_level_for_downsample(self, downsample: float) -> int:
        """Return the closest pyramid level for a requested downsample."""

    def close(self) -> None:
        """Release underlying file handles."""


@runtime_checkable
class SlideReader(Protocol):
    name: str
    priority: int

    def can_open(self, path: str | Path) -> bool:
        """Return True when this reader is a plausible opener for path."""

    def open(self, path: str | Path) -> Slide:
        """Open path and return a normalized Slide."""

