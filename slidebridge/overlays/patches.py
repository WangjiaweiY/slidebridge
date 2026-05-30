from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def load_patches_csv(path: str | Path) -> list[dict[str, Any]]:
    csv_path = Path(path)
    patches: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        fields = {name.strip() for name in reader.fieldnames if name}
        missing = {"x", "y"} - fields
        if missing:
            raise ValueError(f"Patch CSV is missing required columns: {', '.join(sorted(missing))}")

        for row_number, row in enumerate(reader, start=2):
            try:
                patch = {
                    "x": int(round(float(_value(row, "x")))),
                    "y": int(round(float(_value(row, "y")))),
                    "width": int(round(float(_value(row, "width", 256)))),
                    "height": int(round(float(_value(row, "height", 256)))),
                }
                score = _value(row, "score", None)
                if score not in (None, ""):
                    patch["score"] = float(score)
            except Exception as exc:
                raise ValueError(f"Invalid patch CSV row {row_number}: {exc}") from exc
            patches.append(patch)
    return patches


def validate_patches(
    patches: list[dict[str, Any]], slide_width: int, slide_height: int
) -> list[dict[str, Any]]:
    slide_width = max(1, int(slide_width))
    slide_height = max(1, int(slide_height))
    validated: list[dict[str, Any]] = []

    for patch in patches:
        x = int(patch.get("x", 0))
        y = int(patch.get("y", 0))
        width = max(1, int(patch.get("width", 256)))
        height = max(1, int(patch.get("height", 256)))
        warnings: list[str] = []

        if x < 0:
            width += x
            x = 0
            warnings.append("clipped_to_bounds")
        if y < 0:
            height += y
            y = 0
            warnings.append("clipped_to_bounds")

        if x >= slide_width:
            x = slide_width - 1
            width = 1
            warnings.append("outside_slide_bounds")
        if y >= slide_height:
            y = slide_height - 1
            height = 1
            warnings.append("outside_slide_bounds")

        width = min(max(1, width), slide_width - x)
        height = min(max(1, height), slide_height - y)
        if x + int(patch.get("width", width)) > slide_width or y + int(patch.get("height", height)) > slide_height:
            warnings.append("clipped_to_bounds")

        item = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }
        if "score" in patch:
            item["score"] = float(patch["score"])
        if warnings:
            item["warnings"] = sorted(set(warnings))
        validated.append(item)

    return validated


def _value(row: dict[str, Any], key: str, default: Any = None) -> Any:
    value = row.get(key)
    if value in (None, ""):
        return default
    return value

