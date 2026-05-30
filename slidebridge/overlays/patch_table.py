from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import isfinite
from statistics import mean
from typing import Any, Iterable, Literal

import numpy as np

ValidationMode = Literal["clip", "drop", "warn"]


@dataclass(frozen=True)
class PatchRecord:
    x: int
    y: int
    width: int
    height: int
    score: float | None = None
    label: str | None = None
    index: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "x": int(self.x),
            "y": int(self.y),
            "width": int(self.width),
            "height": int(self.height),
        }
        if self.score is not None:
            payload["score"] = float(self.score)
        if self.label is not None:
            payload["label"] = self.label
        if self.index is not None:
            payload["index"] = int(self.index)
        if self.extra:
            payload["extra"] = self.extra
        return payload


@dataclass(frozen=True)
class PatchTable:
    records: list[PatchRecord]
    source: str | None = None
    coordinate_space: str = "level0"
    default_patch_size: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.records)

    def to_list(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.records]

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "coordinate_space": self.coordinate_space,
            "default_patch_size": self.default_patch_size,
            "metadata": self.metadata,
            "patches": self.to_list(),
        }

    def with_scores(self, scores: Iterable[float]) -> "PatchTable":
        values = _score_list(scores)
        if len(values) != len(self.records):
            raise ValueError(f"Score length mismatch: got {len(values)} scores for {len(self.records)} patches.")
        records = [
            replace(record, score=None if value is None else float(value))
            for record, value in zip(self.records, values)
        ]
        return replace(self, records=records)

    def validate(self, width: int, height: int, mode: ValidationMode = "clip") -> "PatchTable":
        if mode not in {"clip", "drop", "warn"}:
            raise ValueError("mode must be one of: clip, drop, warn")
        slide_width = max(1, int(width))
        slide_height = max(1, int(height))
        records: list[PatchRecord] = []
        warnings: list[str] = list(self.metadata.get("warnings", []))
        clipped = 0
        dropped = 0
        outside = 0

        for record in self.records:
            x = int(record.x)
            y = int(record.y)
            patch_w = max(1, int(record.width))
            patch_h = max(1, int(record.height))
            is_outside = x >= slide_width or y >= slide_height or x + patch_w <= 0 or y + patch_h <= 0
            is_partial = x < 0 or y < 0 or x + patch_w > slide_width or y + patch_h > slide_height

            if is_outside:
                outside += 1
                if mode == "drop":
                    dropped += 1
                    continue
                if mode == "clip":
                    clamped_x = min(max(0, x), slide_width - 1)
                    clamped_y = min(max(0, y), slide_height - 1)
                    clipped += 1
                    records.append(
                        replace(
                            _with_warning(record, "outside_slide_bounds"),
                            x=clamped_x,
                            y=clamped_y,
                            width=1,
                            height=1,
                        )
                    )
                    continue
                records.append(_with_warning(record, "outside_slide_bounds"))
                continue

            if not is_partial:
                records.append(record)
                continue

            if mode == "drop":
                dropped += 1
                continue
            if mode == "warn":
                records.append(_with_warning(record, "outside_slide_bounds"))
                continue

            x2 = min(slide_width, x + patch_w)
            y2 = min(slide_height, y + patch_h)
            x1 = max(0, x)
            y1 = max(0, y)
            clipped += 1
            records.append(
                replace(
                    _with_warning(record, "clipped_to_bounds"),
                    x=x1,
                    y=y1,
                    width=max(1, x2 - x1),
                    height=max(1, y2 - y1),
                )
            )

        if clipped:
            warnings.append(f"clipped_to_bounds:{clipped}")
        if outside:
            warnings.append(f"outside_slide_bounds:{outside}")
        if dropped:
            warnings.append(f"dropped_patches:{dropped}")

        metadata = dict(self.metadata)
        metadata["warnings"] = warnings
        metadata["validation"] = {
            "mode": mode,
            "slide_width": slide_width,
            "slide_height": slide_height,
            "input_count": len(self.records),
            "output_count": len(records),
            "clipped": clipped,
            "dropped": dropped,
            "outside": outside,
        }
        return replace(self, records=records, metadata=metadata)

    def normalize_scores(self, method: Literal["minmax", "percentile"] = "minmax") -> "PatchTable":
        if method not in {"minmax", "percentile"}:
            raise ValueError("method must be one of: minmax, percentile")
        values = np.array([record.score for record in self.records if record.score is not None], dtype=float)
        if values.size == 0:
            return self
        if method == "percentile":
            low, high = np.percentile(values, [1, 99])
        else:
            low, high = float(np.min(values)), float(np.max(values))
        if not isfinite(float(low)) or not isfinite(float(high)):
            normalized = [0.0 if record.score is not None else None for record in self.records]
        elif high <= low:
            normalized = [
                None
                if record.score is None
                else float(np.clip(float(record.score), 0.0, 1.0))
                for record in self.records
            ]
        else:
            normalized = [
                None
                if record.score is None
                else float(np.clip((float(record.score) - low) / (high - low), 0.0, 1.0))
                for record in self.records
            ]
        records = [replace(record, score=value) for record, value in zip(self.records, normalized)]
        metadata = dict(self.metadata)
        metadata["score_normalization"] = {"method": method, "low": float(low), "high": float(high)}
        return replace(self, records=records, metadata=metadata)

    def summary(self) -> dict[str, Any]:
        xs = [record.x for record in self.records]
        ys = [record.y for record in self.records]
        widths = [record.width for record in self.records]
        heights = [record.height for record in self.records]
        scores = [record.score for record in self.records if record.score is not None]
        payload: dict[str, Any] = {
            "count": len(self.records),
            "source": self.source,
            "coordinate_space": self.coordinate_space,
            "default_patch_size": self.default_patch_size,
            "has_scores": bool(scores),
            "warnings": list(self.metadata.get("warnings", [])),
        }
        if self.records:
            payload.update(
                {
                    "x_min": min(xs),
                    "x_max": max(xs),
                    "y_min": min(ys),
                    "y_max": max(ys),
                    "width_min": min(widths),
                    "width_max": max(widths),
                    "height_min": min(heights),
                    "height_max": max(heights),
                }
            )
        if scores:
            payload.update(
                {
                    "score_min": float(min(scores)),
                    "score_max": float(max(scores)),
                    "score_mean": float(mean(scores)),
                }
            )
        return payload


def _with_warning(record: PatchRecord, warning: str) -> PatchRecord:
    extra = dict(record.extra)
    warnings = list(extra.get("warnings", []))
    warnings.append(warning)
    extra["warnings"] = sorted(set(warnings))
    return replace(record, extra=extra)


def _score_list(scores: Iterable[float]) -> list[float | None]:
    values: list[float | None] = []
    for value in scores:
        if value is None:
            values.append(None)
        else:
            values.append(float(value))
    return values
