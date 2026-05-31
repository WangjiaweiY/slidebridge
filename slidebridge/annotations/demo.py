from __future__ import annotations

import random
from pathlib import Path

from slidebridge.annotations.io import save_annotation_table
from slidebridge.annotations.table import AnnotationRecord, AnnotationTable
from slidebridge.utils.paths import ensure_parent


def create_demo_annotations(
    out: str | Path,
    width: int = 4096,
    height: int = 3072,
    seed: int = 42,
    count: int = 6,
    labels: list[str] | None = None,
    output_format: str = "geojson",
) -> Path:
    rng = random.Random(seed)
    names = labels or ["Tumor", "Stroma", "Necrosis"]
    colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]
    records: list[AnnotationRecord] = []
    for index in range(max(0, int(count))):
        label = names[index % len(names)]
        color = colors[index % len(colors)]
        cx = rng.uniform(width * 0.15, width * 0.85)
        cy = rng.uniform(height * 0.15, height * 0.85)
        w = rng.uniform(width * 0.08, width * 0.22)
        h = rng.uniform(height * 0.08, height * 0.22)
        if index % 3 == 0:
            ring = _ellipse_polygon(cx, cy, w / 2, h / 2, points=10)
            records.append(AnnotationRecord(str(index), "polygon", [ring], label, color, properties={"synthetic": True}))
        elif index % 3 == 1:
            records.append(
                AnnotationRecord(
                    str(index),
                    "rectangle",
                    {"x": max(0.0, cx - w / 2), "y": max(0.0, cy - h / 2), "width": w, "height": h},
                    label,
                    color,
                    properties={"synthetic": True},
                )
            )
        else:
            records.append(AnnotationRecord(str(index), "point", {"x": cx, "y": cy}, label, color, properties={"synthetic": True}))
    table = AnnotationTable(records=records, source=str(out), source_format="synthetic", metadata={"synthetic": True}).compute_bboxes()
    output = ensure_parent(out)
    if output_format == "asap-xml":
        _write_asap_xml(table, output)
        return output
    fmt = "slidebridge-json" if output_format == "slidebridge-json" else "geojson"
    return save_annotation_table(table, output, format=fmt)


def _ellipse_polygon(cx: float, cy: float, rx: float, ry: float, points: int) -> list[tuple[float, float]]:
    import math

    ring = []
    for index in range(points):
        angle = 2 * math.pi * index / points
        ring.append((cx + math.cos(angle) * rx, cy + math.sin(angle) * ry))
    ring.append(ring[0])
    return ring


def _write_asap_xml(table: AnnotationTable, output: Path) -> None:
    from xml.etree.ElementTree import Element, SubElement, ElementTree

    root = Element("ASAP_Annotations")
    annotations = SubElement(root, "Annotations")
    groups = SubElement(root, "AnnotationGroups")
    seen_groups = set()
    for index, record in enumerate(table.normalize_colors().records):
        label = record.label or "Annotation"
        if label not in seen_groups:
            SubElement(groups, "Group", {"Name": label, "PartOfGroup": "None", "Color": record.color or "#e41a1c"})
            seen_groups.add(label)
        asap_type = {"polygon": "Polygon", "rectangle": "Rectangle", "point": "Dot", "line": "Line"}.get(record.type, "Polygon")
        node = SubElement(
            annotations,
            "Annotation",
            {"Name": record.id or str(index), "Type": asap_type, "PartOfGroup": label, "Color": record.color or "#e41a1c"},
        )
        coords_node = SubElement(node, "Coordinates")
        for order, point in enumerate(_record_points(record)):
            SubElement(coords_node, "Coordinate", {"Order": str(order), "X": str(float(point[0])), "Y": str(float(point[1]))})
    ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def _record_points(record: AnnotationRecord) -> list[tuple[float, float]]:
    if record.type == "polygon":
        return list(record.coordinates[0])
    if record.type == "rectangle":
        x = float(record.coordinates["x"])
        y = float(record.coordinates["y"])
        w = float(record.coordinates["width"])
        h = float(record.coordinates["height"])
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if record.type == "point":
        return [(float(record.coordinates["x"]), float(record.coordinates["y"]))]
    if record.type == "line":
        return list(record.coordinates)
    return []
