from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from slidebridge.annotations.geometry import bbox_intersects, point_in_record, record_area
from slidebridge.annotations.table import AnnotationTable
from slidebridge.overlays.patch_table import PatchRecord, PatchTable
from slidebridge.utils.paths import ensure_parent


LabelMethod = Literal["center", "bbox"]


def label_patch_table(
    patch_table: PatchTable,
    annotation_table: AnnotationTable,
    method: LabelMethod = "center",
    background_label: str = "background",
    multi_label: bool = False,
) -> tuple[PatchTable, dict[str, Any]]:
    if method not in {"center", "bbox"}:
        raise ValueError("method must be one of: center, bbox")
    annotations = annotation_table.compute_bboxes().normalize_colors().records
    records: list[PatchRecord] = []
    counts: dict[str, int] = {}
    labeled = 0
    for patch in patch_table.records:
        matches = _matches(patch, annotations, method)
        if matches:
            labeled += 1
            chosen = matches if multi_label else [_single_label_choice(matches)]
            labels = [record.label or "<unlabeled>" for record in chosen]
            label = ";".join(dict.fromkeys(labels)) if multi_label else labels[0]
            extra = dict(patch.extra)
            extra.update(
                {
                    "matched_annotation_id": ";".join(str(record.id or "") for record in chosen),
                    "matched_annotation_type": ";".join(record.type for record in chosen),
                    "matched_annotation_label": label,
                }
            )
        else:
            label = background_label
            extra = dict(patch.extra)
            extra.update({"matched_annotation_id": "", "matched_annotation_type": "", "matched_annotation_label": background_label})
        counts[label] = counts.get(label, 0) + 1
        records.append(replace(patch, label=label, extra=extra))
    summary = {
        "total_patches": len(patch_table),
        "labeled_patches": labeled,
        "background_patches": len(patch_table) - labeled,
        "label_counts": counts,
        "method": method,
        "multi_label": multi_label,
        "single_label_policy": "smallest_area_then_source_order",
    }
    return replace(patch_table, records=records), summary


def save_labeled_patches(table: PatchTable, path: str | Path, output_format: str | None = None, include_score: bool = True) -> Path:
    output = ensure_parent(path)
    fmt = (output_format or output.suffix.lower().lstrip(".") or "csv").lower()
    if fmt == "csv":
        fieldnames = ["index", "x", "y", "width", "height"]
        if include_score:
            fieldnames.append("score")
        fieldnames += ["label", "matched_annotation_id", "matched_annotation_type", "matched_annotation_label"]
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for index, record in enumerate(table.records):
                row = {
                    "index": record.index if record.index is not None else index,
                    "x": record.x,
                    "y": record.y,
                    "width": record.width,
                    "height": record.height,
                    "label": record.label,
                    "matched_annotation_id": record.extra.get("matched_annotation_id", ""),
                    "matched_annotation_type": record.extra.get("matched_annotation_type", ""),
                    "matched_annotation_label": record.extra.get("matched_annotation_label", ""),
                }
                if include_score:
                    row["score"] = record.score
                writer.writerow(row)
        return output
    if fmt == "json":
        output.write_text(json.dumps(table.to_jsonable(), ensure_ascii=False, indent=2), encoding="utf-8")
        return output
    if fmt == "h5":
        try:
            import h5py
            import numpy as np
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Writing labeled H5 requires h5py and numpy.") from exc
        with h5py.File(output, "w") as handle:
            handle.create_dataset("coords", data=np.array([[r.x, r.y, r.width, r.height] for r in table.records], dtype="int64"))
            labels = [record.label or "" for record in table.records]
            handle.create_dataset("labels", data=[label.encode("utf-8") for label in labels])
            if include_score:
                handle.create_dataset("scores", data=np.array([float(r.score or 0.0) for r in table.records], dtype="float32"))
        return output
    raise ValueError("--output-format must be one of: csv, json, h5")


def _matches(patch: PatchRecord, annotations: list[Any], method: LabelMethod) -> list[Any]:
    if method == "center":
        x = patch.x + patch.width / 2.0
        y = patch.y + patch.height / 2.0
        return [annotation for annotation in annotations if point_in_record(x, y, annotation)]
    patch_bbox = (patch.x, patch.y, patch.x + patch.width, patch.y + patch.height)
    return [annotation for annotation in annotations if annotation.bbox and bbox_intersects(patch_bbox, annotation.bbox)]


def _single_label_choice(records: list[Any]) -> Any:
    return sorted(enumerate(records), key=lambda item: (record_area(item[1]) if record_area(item[1]) is not None else float("inf"), item[0]))[0][1]
