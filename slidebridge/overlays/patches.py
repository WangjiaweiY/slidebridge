from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from slidebridge.overlays.patch_table import PatchRecord, PatchTable

COORD_KEYS = ("coords", "coordinates", "patch_coords")
SCORE_KEYS = ("scores", "score", "attention", "attentions", "attention_scores", "logits", "probs")


def load_patch_table(
    path: str | Path,
    default_patch_size: int = 256,
    score_path: str | Path | None = None,
) -> PatchTable:
    patch_path = Path(path)
    suffix = patch_path.suffix.lower()
    if suffix == ".csv":
        table = _load_csv(patch_path, default_patch_size)
    elif suffix == ".npy":
        table = _load_npy(patch_path, default_patch_size)
    elif suffix in {".h5", ".hdf5"}:
        table = _load_h5(patch_path, default_patch_size)
    elif suffix == ".json":
        table = _load_json(patch_path, default_patch_size)
    elif suffix in {".pt", ".pth"}:
        table = _load_torch(patch_path, default_patch_size)
    else:
        raise ValueError(f"Unsupported patch coordinate format: {suffix or '<none>'}")

    if score_path is not None:
        from slidebridge.overlays.heatmap import attach_scores, load_scores

        table = attach_scores(table, load_scores(score_path))
    return table


def load_patches_csv(path: str | Path) -> list[dict[str, Any]]:
    return load_patch_table(path).to_list()


def validate_patches(
    patches: list[dict[str, Any]], slide_width: int, slide_height: int
) -> list[dict[str, Any]]:
    records = [_record_from_mapping(patch, 256, idx) for idx, patch in enumerate(patches)]
    return PatchTable(records=records).validate(slide_width, slide_height, mode="clip").to_list()


def _load_csv(path: Path, default_patch_size: int) -> PatchTable:
    records: list[PatchRecord] = []
    warnings: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return PatchTable(records=[], source=str(path), default_patch_size=default_patch_size)
        fields = {name.strip() for name in reader.fieldnames if name}
        missing = {"x", "y"} - fields
        if missing:
            raise ValueError(f"Patch CSV is missing required columns: {', '.join(sorted(missing))}")
        for row_number, row in enumerate(reader, start=2):
            try:
                records.append(_record_from_mapping(row, default_patch_size, len(records)))
            except Exception as exc:
                raise ValueError(f"Invalid patch CSV row {row_number}: {exc}") from exc
    metadata = {"format": "csv"}
    if warnings:
        metadata["warnings"] = warnings
    return PatchTable(records=records, source=str(path), default_patch_size=default_patch_size, metadata=metadata)


def _load_npy(path: Path, default_patch_size: int) -> PatchTable:
    array = np.load(path, allow_pickle=False)
    records = _records_from_array(array, default_patch_size)
    return PatchTable(
        records=records,
        source=str(path),
        default_patch_size=default_patch_size,
        metadata={"format": "npy", "shape": list(array.shape)},
    )


def _load_h5(path: Path, default_patch_size: int) -> PatchTable:
    try:
        import h5py
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("Loading .h5/.hdf5 patch files requires h5py. Please install h5py.") from exc

    warnings: list[str] = []
    with h5py.File(path, "r") as handle:
        coord_key = _first_existing_key(handle, COORD_KEYS)
        if coord_key is None:
            raise ValueError(f"No coordinate dataset found in {path}. Expected one of: {', '.join(COORD_KEYS)}")
        coords = np.asarray(handle[coord_key])
        attrs = _jsonable_attrs(handle.attrs)
        for key in ("patch_size", "patch_level", "downsample", "mpp"):
            if key in handle[coord_key].attrs:
                attrs[key] = _jsonable_value(handle[coord_key].attrs[key])
        patch_size = _patch_size_from_attrs(attrs, default_patch_size)
        records = _records_from_array(coords, patch_size)
        score_key = _first_existing_key(handle, SCORE_KEYS)
        if score_key is not None:
            scores = _flatten_scores(np.asarray(handle[score_key]), warnings)
            if len(scores) == len(records):
                records = PatchTable(records).with_scores(scores).records
            else:
                warnings.append(f"score_length_mismatch:{len(scores)}:{len(records)}")
        metadata = {"format": "h5", "coord_key": coord_key, "attrs": attrs}
        if score_key is not None:
            metadata["score_key"] = score_key
        if warnings:
            metadata["warnings"] = warnings
        return PatchTable(records=records, source=str(path), default_patch_size=patch_size, metadata=metadata)


def _load_json(path: Path, default_patch_size: int) -> PatchTable:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        patches = payload.get("patches")
        metadata = {key: value for key, value in payload.items() if key != "patches"}
    else:
        patches = payload
        metadata = {}
    if not isinstance(patches, list):
        raise ValueError("Patch JSON must be a list or an object with a 'patches' list")
    records = [_record_from_mapping(item, default_patch_size, idx) for idx, item in enumerate(patches)]
    metadata["format"] = "json"
    return PatchTable(records=records, source=str(path), default_patch_size=default_patch_size, metadata=metadata)


def _load_torch(path: Path, default_patch_size: int) -> PatchTable:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Loading .pt/.pth requires PyTorch. Please install torch or export your coordinates to CSV/NPY/H5."
        ) from exc
    payload = torch.load(path, map_location="cpu")
    warnings: list[str] = []
    if isinstance(payload, dict):
        coord_key = next((key for key in COORD_KEYS if key in payload), None)
        if coord_key is None:
            raise ValueError(f"No coordinate tensor found. Expected one of: {', '.join(COORD_KEYS)}")
        coords = _torch_to_numpy(payload[coord_key])
        records = _records_from_array(coords, default_patch_size)
        score_key = next((key for key in SCORE_KEYS if key in payload), None)
        if score_key is not None:
            scores = _flatten_scores(_torch_to_numpy(payload[score_key]), warnings)
            if len(scores) == len(records):
                records = PatchTable(records).with_scores(scores).records
            else:
                warnings.append(f"score_length_mismatch:{len(scores)}:{len(records)}")
        metadata = {"format": "pt", "coord_key": coord_key}
        if score_key is not None:
            metadata["score_key"] = score_key
    else:
        records = _records_from_array(_torch_to_numpy(payload), default_patch_size)
        metadata = {"format": "pt"}
    if warnings:
        metadata["warnings"] = warnings
    return PatchTable(records=records, source=str(path), default_patch_size=default_patch_size, metadata=metadata)


def _record_from_mapping(row: dict[str, Any], default_patch_size: int, index: int) -> PatchRecord:
    score = _first_value(row, ("score", "attention"))
    label = _first_value(row, ("label",))
    record_index = _first_value(row, ("index",))
    known = {"x", "y", "width", "height", "score", "attention", "label", "index"}
    extra = {key: value for key, value in row.items() if key not in known and value not in (None, "")}
    return PatchRecord(
        x=int(round(float(_required(row, "x")))),
        y=int(round(float(_required(row, "y")))),
        width=max(1, int(round(float(_value(row, "width", default_patch_size))))),
        height=max(1, int(round(float(_value(row, "height", default_patch_size))))),
        score=None if score in (None, "") else float(score),
        label=None if label in (None, "") else str(label),
        index=index if record_index in (None, "") else int(round(float(record_index))),
        extra=extra,
    )


def _records_from_array(array: np.ndarray, default_patch_size: int) -> list[PatchRecord]:
    if array.ndim != 2:
        raise ValueError(f"Coordinate array must be 2D, got shape {array.shape}")
    if array.shape[1] < 2:
        raise ValueError(f"Coordinate array must have at least 2 columns, got shape {array.shape}")
    records: list[PatchRecord] = []
    for idx, row in enumerate(array):
        width = default_patch_size if array.shape[1] < 4 else int(round(float(row[2])))
        height = default_patch_size if array.shape[1] < 4 else int(round(float(row[3])))
        score = None if array.shape[1] < 5 else float(row[4])
        extra = {}
        if array.shape[1] > 5:
            extra["columns_5_plus"] = [float(value) for value in row[5:].tolist()]
        records.append(
            PatchRecord(
                x=int(round(float(row[0]))),
                y=int(round(float(row[1]))),
                width=max(1, width),
                height=max(1, height),
                score=score,
                index=idx,
                extra=extra,
            )
        )
    return records


def _flatten_scores(array: np.ndarray, warnings: list[str]) -> list[float]:
    scores = np.asarray(array)
    if scores.ndim == 2 and scores.shape[1] == 1:
        scores = scores[:, 0]
    elif scores.ndim == 2 and scores.shape[1] > 1:
        warnings.append(f"score_array_2d_using_last_column:{scores.shape[1]}")
        scores = scores[:, -1]
    elif scores.ndim != 1:
        scores = scores.reshape(-1)
        warnings.append("score_array_flattened")
    return [float(value) for value in scores.tolist()]


def _first_existing_key(handle: Any, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in handle:
            return key
    return None


def _jsonable_attrs(attrs: Any) -> dict[str, Any]:
    return {str(key): _jsonable_value(value) for key, value in attrs.items()}


def _jsonable_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _patch_size_from_attrs(attrs: dict[str, Any], default_patch_size: int) -> int:
    value = attrs.get("patch_size", default_patch_size)
    if isinstance(value, (list, tuple)) and value:
        value = value[0]
    try:
        return max(1, int(round(float(value))))
    except (TypeError, ValueError):
        return default_patch_size


def _torch_to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def _first_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _required(row: dict[str, Any], key: str) -> Any:
    value = _value(row, key, None)
    if value in (None, ""):
        raise ValueError(f"missing required value: {key}")
    return value


def _value(row: dict[str, Any], key: str, default: Any = None) -> Any:
    value = row.get(key)
    if value in (None, ""):
        return default
    return value

