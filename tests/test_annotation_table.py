from __future__ import annotations

from slidebridge.annotations.table import AnnotationRecord, AnnotationTable


def test_annotation_table_basic_summary_and_labels():
    table = AnnotationTable(
        records=[
            AnnotationRecord("a", "rectangle", {"x": 1, "y": 2, "width": 10, "height": 20}, "Tumor", "#ff0000"),
            AnnotationRecord("b", "point", {"x": 5, "y": 6}, "Stroma", None),
        ],
        source="demo",
        source_format="synthetic",
    ).compute_bboxes().normalize_colors()

    assert len(table) == 2
    assert table.labels() == ["Stroma", "Tumor"]
    assert table.summary()["type_counts"] == {"rectangle": 1, "point": 1}
    assert table.summary()["global_bbox"] == [1.0, 2.0, 11.0, 22.0]
    assert table.to_jsonable()["coordinate_space"] == "level0"


def test_annotation_filter_labels():
    table = AnnotationTable(
        [
            AnnotationRecord(type="point", coordinates={"x": 1, "y": 1}, label="Tumor"),
            AnnotationRecord(type="point", coordinates={"x": 2, "y": 2}, label="Normal"),
        ]
    )

    filtered = table.filter_labels(["Tumor"])

    assert len(filtered) == 1
    assert filtered.records[0].label == "Tumor"


def test_annotation_validate_warn_and_drop():
    table = AnnotationTable(
        [
            AnnotationRecord(type="rectangle", coordinates={"x": 10, "y": 10, "width": 20, "height": 20}),
            AnnotationRecord(type="rectangle", coordinates={"x": 999, "y": 999, "width": 20, "height": 20}),
            AnnotationRecord(type="polygon", coordinates=[]),
        ]
    ).compute_bboxes()

    warned = table.validate(100, 100, mode="warn")
    dropped = table.validate(100, 100, mode="drop")

    assert len(warned) == 3
    assert any("outside_slide_bounds" in item for item in warned.metadata["warnings"])
    assert len(dropped) == 1


def test_annotation_to_list_contains_bbox():
    record = AnnotationRecord(type="rectangle", coordinates={"x": 1, "y": 2, "width": 3, "height": 4})
    table = AnnotationTable([record]).compute_bboxes()

    assert table.to_list()[0]["bbox"] == [1.0, 2.0, 4.0, 6.0]
