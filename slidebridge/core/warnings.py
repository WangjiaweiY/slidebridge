from __future__ import annotations

from typing import Any


def collect_warnings(info: dict[str, Any]) -> list[str]:
    warnings: list[str] = []

    mpp_x = _as_float(info.get("mpp_x"))
    mpp_y = _as_float(info.get("mpp_y"))
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    objective = _as_float(info.get("objective_power"))

    if mpp_x is None or mpp_y is None:
        warnings.append("missing_mpp")
    elif mpp_x > 0 and mpp_y > 0:
        mean = (mpp_x + mpp_y) / 2.0
        if mean and abs(mpp_x - mpp_y) / mean > 0.02:
            warnings.append("mpp_x_y_mismatch")

    if _has_irregular_level_downsample(info):
        warnings.append("irregular_level_downsample")

    if _has_suspicious_objective_mpp(objective, mpp_x, mpp_y):
        warnings.append("suspicious_objective_mpp")

    if width * height > 100_000 * 100_000:
        warnings.append("huge_slide")

    return warnings


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_irregular_level_downsample(info: dict[str, Any]) -> bool:
    dims = info.get("level_dimensions") or []
    downsamples = info.get("level_downsamples") or []
    if len(dims) < 2 or len(dims) != len(downsamples):
        return False

    width0 = float(info.get("width") or 0)
    height0 = float(info.get("height") or 0)
    if width0 <= 0 or height0 <= 0:
        return False

    for dim, reported in zip(dims[1:], downsamples[1:]):
        try:
            level_w, level_h = float(dim[0]), float(dim[1])
            reported_ds = float(reported)
        except (TypeError, ValueError, IndexError):
            continue
        if level_w <= 0 or level_h <= 0 or reported_ds <= 0:
            continue
        inferred_x = width0 / level_w
        inferred_y = height0 / level_h
        inferred = (inferred_x + inferred_y) / 2.0
        if inferred and abs(reported_ds - inferred) / inferred > 0.10:
            return True
    return False


def _has_suspicious_objective_mpp(
    objective: float | None, mpp_x: float | None, mpp_y: float | None
) -> bool:
    if objective is None or mpp_x is None or mpp_y is None:
        return False
    mpp = (mpp_x + mpp_y) / 2.0
    if objective >= 35 and mpp > 0.8:
        return True
    if 15 <= objective <= 25 and mpp < 0.2:
        return True
    return False

