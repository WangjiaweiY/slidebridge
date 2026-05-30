from __future__ import annotations

from slidebridge.annotations.geometry import (
    bbox_contains_point,
    bbox_intersects,
    point_in_polygon,
    point_in_record,
    polygon_area,
    record_area,
)
from slidebridge.annotations.table import AnnotationRecord


def test_point_in_polygon_square():
    square = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]

    assert point_in_polygon(5, 5, square) is True
    assert point_in_polygon(20, 5, square) is False


def test_polygon_with_hole():
    exterior = [(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)]
    hole = [(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)]
    record = AnnotationRecord(type="polygon", coordinates=[exterior, hole])

    assert point_in_record(2, 2, record) is True
    assert point_in_record(10, 10, record) is False


def test_bbox_helpers():
    assert bbox_intersects((0, 0, 10, 10), (5, 5, 20, 20)) is True
    assert bbox_intersects((0, 0, 10, 10), (11, 11, 20, 20)) is False
    assert bbox_contains_point((0, 0, 10, 10), 3, 4) is True


def test_rectangle_contains_point():
    record = AnnotationRecord(type="rectangle", coordinates={"x": 10, "y": 10, "width": 20, "height": 20})

    assert point_in_record(15, 15, record) is True
    assert point_in_record(40, 15, record) is False


def test_multipolygon_contains_point_and_area():
    poly1 = [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]]
    poly2 = [[(20, 20), (30, 20), (30, 30), (20, 30), (20, 20)]]
    record = AnnotationRecord(type="multipolygon", coordinates=[poly1, poly2])

    assert point_in_record(5, 5, record) is True
    assert point_in_record(25, 25, record) is True
    assert record_area(record) == 200.0
    assert polygon_area(poly1[0]) == 100.0
