from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from slidebridge.annotations.geometry import compute_record_bbox
from slidebridge.annotations.table import AnnotationRecord, AnnotationTable, normalize_color


def load_asap_xml(path: str | Path) -> AnnotationTable:
    source = Path(path)
    tree = ET.parse(source)
    root = tree.getroot()
    group_colors = {
        group.attrib.get("Name"): normalize_color(group.attrib.get("Color"))
        for group in root.findall(".//AnnotationGroups/Group")
    }
    records: list[AnnotationRecord] = []
    warnings: list[str] = []
    for index, node in enumerate(root.findall(".//Annotations/Annotation")):
        record = _record_from_node(node, index, str(source), group_colors, warnings)
        if record is not None:
            records.append(record)
    table = AnnotationTable(
        records=records,
        source=str(source),
        source_format="asap-xml",
        metadata={"warnings": warnings} if warnings else {},
    )
    return table.compute_bboxes().normalize_colors()


def _record_from_node(
    node: ET.Element,
    index: int,
    source: str,
    group_colors: dict[str | None, str | None],
    warnings: list[str],
) -> AnnotationRecord | None:
    attrs = dict(node.attrib)
    raw_type = attrs.get("Type", "Unknown")
    group = attrs.get("PartOfGroup")
    name = attrs.get("Name")
    label = group or name or raw_type
    color = normalize_color(attrs.get("Color")) or group_colors.get(group)
    coords = _coordinates(node)
    if not coords:
        warnings.append(f"missing_coordinates:{name or index}")
        return None
    normalized_type = raw_type.lower()
    properties = {"asap": attrs}
    if normalized_type == "polygon":
        record = AnnotationRecord(str(index), "polygon", [coords], label, color, source=source, properties=properties)
    elif normalized_type == "rectangle":
        xs = [point[0] for point in coords]
        ys = [point[1] for point in coords]
        record = AnnotationRecord(
            str(index),
            "rectangle",
            {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)},
            label,
            color,
            source=source,
            properties=properties,
        )
    elif normalized_type in {"dot", "point"}:
        record = AnnotationRecord(str(index), "point", {"x": coords[0][0], "y": coords[0][1]}, label, color, source=source, properties=properties)
    elif normalized_type == "line":
        record = AnnotationRecord(str(index), "line", coords, label, color, source=source, properties=properties)
    elif normalized_type == "spline":
        warnings.append(f"spline_approximated_as_line:{name or index}")
        record = AnnotationRecord(str(index), "line", coords, label, color, source=source, properties=properties)
    else:
        warnings.append(f"unknown_annotation_type:{raw_type}")
        record = AnnotationRecord(str(index), "unknown", coords, label, color, source=source, properties=properties)
    return record.__class__(**{**record.to_dict(), "bbox": compute_record_bbox(record)})


def _coordinates(node: ET.Element) -> list[tuple[float, float]]:
    points = []
    for coord in node.findall(".//Coordinates/Coordinate"):
        try:
            order = int(float(coord.attrib.get("Order", len(points))))
            point = (float(coord.attrib["X"]), float(coord.attrib["Y"]))
            points.append((order, point))
        except (KeyError, ValueError):
            continue
    return [point for _, point in sorted(points, key=lambda item: item[0])]
