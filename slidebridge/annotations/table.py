from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal


AnnotationType = Literal["polygon", "multipolygon", "rectangle", "point", "line", "unknown"]
ValidationMode = Literal["warn", "drop", "clip"]


@dataclass(frozen=True)
class AnnotationRecord:
    id: str | None = None
    type: str = "unknown"
    coordinates: Any = None
    label: str | None = None
    color: str | None = None
    confidence: float | None = None
    source: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    bbox: tuple[float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "coordinates": self.coordinates,
            "label": self.label,
            "color": self.color,
            "confidence": self.confidence,
            "source": self.source,
            "properties": self.properties,
            "bbox": list(self.bbox) if self.bbox is not None else None,
        }
        return payload


@dataclass(frozen=True)
class AnnotationTable:
    records: list[AnnotationRecord]
    source: str | None = None
    source_format: str | None = None
    coordinate_space: str = "level0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.records)

    def to_list(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.records]

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "type": "SlideBridgeAnnotationTable",
            "version": "0.2.1",
            "coordinate_space": self.coordinate_space,
            "source": self.source,
            "source_format": self.source_format,
            "metadata": self.metadata,
            "annotations": self.to_list(),
        }

    def labels(self) -> list[str]:
        return sorted({record.label for record in self.records if record.label})

    def summary(self) -> dict[str, Any]:
        from slidebridge.annotations.geometry import compute_record_bbox

        type_counts = Counter(record.type for record in self.records)
        label_counts = Counter(record.label or "<unlabeled>" for record in self.records)
        bboxes = [record.bbox or compute_record_bbox(record) for record in self.records]
        valid_bboxes = [bbox for bbox in bboxes if bbox is not None]
        global_bbox = None
        if valid_bboxes:
            global_bbox = [
                min(bbox[0] for bbox in valid_bboxes),
                min(bbox[1] for bbox in valid_bboxes),
                max(bbox[2] for bbox in valid_bboxes),
                max(bbox[3] for bbox in valid_bboxes),
            ]
        return {
            "count": len(self.records),
            "source": self.source,
            "source_format": self.source_format,
            "coordinate_space": self.coordinate_space,
            "type_counts": dict(type_counts),
            "label_counts": dict(label_counts),
            "labels": self.labels(),
            "global_bbox": global_bbox,
            "colors_present": sorted({record.color for record in self.records if record.color}),
            "warnings": list(self.metadata.get("warnings", [])),
        }

    def validate(self, width: int | None = None, height: int | None = None, mode: ValidationMode = "warn") -> "AnnotationTable":
        if mode not in {"warn", "drop", "clip"}:
            raise ValueError("mode must be one of: warn, drop, clip")
        from slidebridge.annotations.geometry import compute_record_bbox

        warnings = list(self.metadata.get("warnings", []))
        records: list[AnnotationRecord] = []
        outside = 0
        invalid = 0
        for record in self.records:
            bbox = record.bbox or compute_record_bbox(record)
            if bbox is None:
                invalid += 1
                if mode == "drop":
                    continue
                records.append(_record_with_warning(record, "invalid_geometry"))
                continue
            if width is not None and height is not None:
                out = bbox[2] < 0 or bbox[3] < 0 or bbox[0] > width or bbox[1] > height
                partial = bbox[0] < 0 or bbox[1] < 0 or bbox[2] > width or bbox[3] > height
                if out or partial:
                    outside += 1
                    if mode == "drop" and out:
                        continue
                    records.append(_record_with_warning(replace(record, bbox=bbox), "outside_slide_bounds"))
                    continue
            records.append(replace(record, bbox=bbox))
        if invalid:
            warnings.append(f"invalid_geometry:{invalid}")
        if outside:
            warnings.append(f"outside_slide_bounds:{outside}")
        metadata = dict(self.metadata)
        metadata["warnings"] = warnings
        return replace(self, records=records, metadata=metadata)

    def filter_labels(self, labels: list[str]) -> "AnnotationTable":
        wanted = {label.strip() for label in labels if label.strip()}
        if not wanted:
            return self
        return replace(self, records=[record for record in self.records if record.label in wanted])

    def compute_bboxes(self) -> "AnnotationTable":
        from slidebridge.annotations.geometry import compute_record_bbox

        return replace(self, records=[replace(record, bbox=record.bbox or compute_record_bbox(record)) for record in self.records])

    def normalize_colors(self) -> "AnnotationTable":
        labels = self.labels()
        palette = [
            "#e41a1c",
            "#377eb8",
            "#4daf4a",
            "#984ea3",
            "#ff7f00",
            "#a65628",
            "#f781bf",
            "#999999",
        ]
        label_colors = {label: palette[index % len(palette)] for index, label in enumerate(labels)}
        records = []
        for index, record in enumerate(self.records):
            color = normalize_color(record.color)
            if color is None:
                color = label_colors.get(record.label or "", palette[index % len(palette)])
            records.append(replace(record, color=color))
        return replace(self, records=records)

    def to_slidebridge_json(self, path: str | Path) -> Path:
        from slidebridge.annotations.io import save_annotation_table

        return save_annotation_table(self, path, format="slidebridge-json")

    @classmethod
    def from_slidebridge_json(cls, path: str | Path) -> "AnnotationTable":
        from slidebridge.annotations.io import load_annotation_table

        return load_annotation_table(path, format="slidebridge-json")


def normalize_color(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return f"#{value & 0xFFFFFF:06x}"
    text = str(value).strip()
    if text.startswith("#") and len(text) == 7:
        return text.lower()
    if text.startswith("0x"):
        try:
            return f"#{int(text, 16) & 0xFFFFFF:06x}"
        except ValueError:
            return None
    try:
        return f"#{int(text) & 0xFFFFFF:06x}"
    except ValueError:
        return None


def _record_with_warning(record: AnnotationRecord, warning: str) -> AnnotationRecord:
    properties = dict(record.properties)
    warnings = list(properties.get("warnings", []))
    warnings.append(warning)
    properties["warnings"] = sorted(set(warnings))
    return replace(record, properties=properties)
