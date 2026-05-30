from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from slidebridge.overlays.patch_table import PatchTable

SCORE_COLUMNS = ("score", "attention", "prob", "probability", "logit")
SCORE_KEYS = ("scores", "score", "attention", "attentions", "attention_scores", "probs", "probabilities", "logits")


def load_scores(path: str | Path) -> list[float]:
    score_path = Path(path)
    suffix = score_path.suffix.lower()
    warnings: list[str] = []
    if suffix == ".csv":
        scores = _scores_from_csv(score_path)
    elif suffix == ".npy":
        scores = _flatten_scores(np.load(score_path, allow_pickle=False), warnings)
    elif suffix in {".h5", ".hdf5"}:
        scores = _scores_from_h5(score_path, warnings)
    elif suffix in {".pt", ".pth"}:
        scores = _scores_from_torch(score_path, warnings)
    else:
        raise ValueError(f"Unsupported score format: {suffix or '<none>'}")
    return scores


def attach_scores(patch_table: PatchTable, scores: Any) -> PatchTable:
    values = _flatten_scores(np.asarray(scores), []) if not isinstance(scores, list) else scores
    if len(values) != len(patch_table):
        raise ValueError(f"Score length mismatch: got {len(values)} scores for {len(patch_table)} patches.")
    return patch_table.with_scores(values)


def _scores_from_csv(path: Path) -> list[float]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        key = next((name for name in SCORE_COLUMNS if name in reader.fieldnames), None)
        if key is None:
            raise ValueError(f"Score CSV must contain one of: {', '.join(SCORE_COLUMNS)}")
        return [float(row[key]) for row in reader if row.get(key) not in (None, "")]


def _scores_from_h5(path: Path, warnings: list[str]) -> list[float]:
    try:
        import h5py
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("Loading .h5/.hdf5 score files requires h5py. Please install h5py.") from exc

    with h5py.File(path, "r") as handle:
        key = next((name for name in SCORE_KEYS if name in handle), None)
        if key is None:
            raise ValueError(f"No score dataset found in {path}. Expected one of: {', '.join(SCORE_KEYS)}")
        return _flatten_scores(np.asarray(handle[key]), warnings)


def _scores_from_torch(path: Path, warnings: list[str]) -> list[float]:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Loading .pt/.pth requires PyTorch. Please install torch or export your scores to CSV/NPY/H5."
        ) from exc
    payload = torch.load(path, map_location="cpu")
    if isinstance(payload, dict):
        key = next((name for name in SCORE_KEYS if name in payload), None)
        if key is None:
            raise ValueError(f"No score tensor found. Expected one of: {', '.join(SCORE_KEYS)}")
        payload = payload[key]
    if hasattr(payload, "detach"):
        payload = payload.detach().cpu().numpy()
    return _flatten_scores(np.asarray(payload), warnings)


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

