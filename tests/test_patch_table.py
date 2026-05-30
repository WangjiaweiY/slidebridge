from __future__ import annotations

import pytest

from slidebridge.overlays.patch_table import PatchRecord, PatchTable


def test_patch_table_basic_to_list_and_summary():
    table = PatchTable([PatchRecord(10, 20, 30, 40, score=0.5, index=0)], source="x.csv")

    assert len(table) == 1
    assert table.to_list()[0]["score"] == 0.5
    assert table.summary()["count"] == 1
    assert table.summary()["score_mean"] == 0.5


def test_patch_table_validate_clip():
    table = PatchTable([PatchRecord(-5, -5, 20, 20)])

    clipped = table.validate(100, 100, mode="clip")

    assert clipped.records[0].x == 0
    assert clipped.records[0].y == 0
    assert clipped.records[0].width == 15
    assert clipped.records[0].height == 15


def test_patch_table_validate_drop():
    table = PatchTable([PatchRecord(-5, -5, 20, 20), PatchRecord(10, 10, 20, 20)])

    dropped = table.validate(100, 100, mode="drop")

    assert len(dropped) == 1
    assert dropped.records[0].x == 10


def test_patch_table_validate_warn():
    table = PatchTable([PatchRecord(-5, -5, 20, 20)])

    warned = table.validate(100, 100, mode="warn")

    assert len(warned) == 1
    assert warned.records[0].x == -5
    assert "outside_slide_bounds" in warned.records[0].extra["warnings"]


def test_patch_table_normalize_scores():
    table = PatchTable([PatchRecord(0, 0, 1, 1, score=10), PatchRecord(1, 1, 1, 1, score=20)])

    normalized = table.normalize_scores("minmax")

    assert normalized.records[0].score == 0.0
    assert normalized.records[1].score == 1.0


def test_patch_table_with_scores_length_match():
    table = PatchTable([PatchRecord(0, 0, 1, 1), PatchRecord(1, 1, 1, 1)])

    scored = table.with_scores([0.2, 0.8])

    assert scored.records[1].score == 0.8


def test_patch_table_with_scores_length_mismatch():
    table = PatchTable([PatchRecord(0, 0, 1, 1)])

    with pytest.raises(ValueError, match="Score length mismatch"):
        table.with_scores([0.1, 0.2])

