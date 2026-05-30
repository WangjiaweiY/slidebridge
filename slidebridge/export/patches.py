from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from slidebridge.core.protocol import Slide
from slidebridge.overlays.patch_table import PatchTable
from slidebridge.utils.image import ensure_rgb


def export_patches(
    slide: Slide,
    patch_table: PatchTable,
    out_dir: str | Path,
    image_format: str = "jpg",
    jpeg_quality: int = 90,
    limit: int | None = None,
    prefix: str = "patch",
    overwrite: bool = False,
    manifest_filename: str = "manifest.csv",
) -> dict[str, Any]:
    fmt = image_format.lower()
    if fmt not in {"jpg", "jpeg", "png"}:
        raise ValueError("image_format must be one of: jpg, png")
    ext = "jpg" if fmt == "jpeg" else fmt
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / manifest_filename
    slide_width, slide_height = slide.dimensions
    records = patch_table.records[:limit] if limit is not None else patch_table.records

    exported = 0
    skipped = 0
    failed = 0
    rows: list[dict[str, Any]] = []

    for ordinal, record in enumerate(records):
        x = int(record.x)
        y = int(record.y)
        width = max(1, int(record.width))
        height = max(1, int(record.height))
        if x >= slide_width or y >= slide_height or x + width <= 0 or y + height <= 0:
            skipped += 1
            continue

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(slide_width, x + width)
        y2 = min(slide_height, y + height)
        export_w = max(1, x2 - x1)
        export_h = max(1, y2 - y1)
        image_name = f"{prefix}_{ordinal:06d}_x{x1}_y{y1}_w{export_w}_h{export_h}.{ext}"
        image_path = output_dir / image_name
        if image_path.exists() and not overwrite:
            skipped += 1
            rows.append(_manifest_row(record, ordinal, x1, y1, export_w, export_h, image_path))
            continue

        try:
            image = ensure_rgb(slide.read_region(x1, y1, export_w, export_h, level=0))
            if ext == "png":
                image.save(image_path, format="PNG")
            else:
                image.save(image_path, format="JPEG", quality=int(jpeg_quality))
            exported += 1
            rows.append(_manifest_row(record, ordinal, x1, y1, export_w, export_h, image_path))
        except Exception:
            failed += 1

    _write_manifest(manifest_path, rows)
    return {
        "exported": exported,
        "skipped": skipped,
        "failed": failed,
        "out_dir": str(output_dir),
        "manifest": str(manifest_path),
    }


def _manifest_row(
    record: Any,
    ordinal: int,
    x: int,
    y: int,
    width: int,
    height: int,
    image_path: Path,
) -> dict[str, Any]:
    return {
        "index": record.index if record.index is not None else ordinal,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "score": "" if record.score is None else record.score,
        "label": "" if record.label is None else record.label,
        "image_path": str(image_path),
    }


def _write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["index", "x", "y", "width", "height", "score", "label", "image_path"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
