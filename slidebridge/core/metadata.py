from __future__ import annotations

from typing import Any

from slidebridge.core.protocol import Slide
from slidebridge.core.warnings import collect_warnings


def summary(slide: Slide) -> dict[str, Any]:
    mpp_x, mpp_y = slide.mpp
    width, height = slide.dimensions
    info: dict[str, Any] = {
        "path": str(slide.path),
        "filename": slide.path.name,
        "reader": slide.reader_name,
        "width": int(width),
        "height": int(height),
        "level_count": int(slide.level_count),
        "level_dimensions": [[int(w), int(h)] for w, h in slide.level_dimensions],
        "level_downsamples": [float(value) for value in slide.level_downsamples],
        "mpp_x": mpp_x,
        "mpp_y": mpp_y,
        "objective_power": slide.objective_power,
        "vendor": slide.vendor,
        "has_mpp": mpp_x is not None and mpp_y is not None,
    }
    info["warnings"] = collect_warnings(info)
    return info

