from __future__ import annotations

import numpy as np
import pytest

from slidebridge.overlays.heatmap import attach_scores, load_scores
from slidebridge.overlays.patch_table import PatchRecord, PatchTable


def test_load_scores_from_npy_vector(tmp_path):
    path = tmp_path / "scores.npy"
    np.save(path, np.array([0.1, 0.2], dtype=np.float32))

    scores = load_scores(path)

    assert scores == pytest.approx([0.1, 0.2])


def test_load_scores_from_npy_matrix_uses_last_column(tmp_path):
    path = tmp_path / "scores.npy"
    np.save(path, np.array([[0.1, 0.9], [0.8, 0.2]], dtype=np.float32))

    scores = load_scores(path)

    assert scores == pytest.approx([0.9, 0.2])


def test_load_scores_from_csv(tmp_path):
    path = tmp_path / "scores.csv"
    path.write_text("x,y,attention\n1,2,0.7\n3,4,0.8\n", encoding="utf-8")

    scores = load_scores(path)

    assert scores == [0.7, 0.8]


def test_attach_scores_success():
    table = PatchTable([PatchRecord(0, 0, 1, 1), PatchRecord(1, 1, 1, 1)])

    scored = attach_scores(table, [0.25, 0.75])

    assert scored.records[0].score == 0.25
    assert scored.records[1].score == 0.75


def test_attach_scores_length_mismatch():
    table = PatchTable([PatchRecord(0, 0, 1, 1)])

    with pytest.raises(ValueError, match="Score length mismatch"):
        attach_scores(table, [0.1, 0.2])

