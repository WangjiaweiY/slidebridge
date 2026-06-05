from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import xml.etree.ElementTree as ET

from slidebridge.annotations.geometry import compute_record_bbox
from slidebridge.annotations.table import AnnotationRecord, AnnotationTable, normalize_color


def load_aperio_xml(path: str | Path) -> AnnotationTable:
    source = Path(path)
    tree = ET.parse(source)
    root = tree.getroot()
    records: list[AnnotationRecord] = []
    warnings: list[str] = []
    for annotation_index, annotation in enumerate(root.findall(".//Annotation")):
        annotation_attrs = dict(annotation.attrib)
        annotation_label = annotation_attrs.get("Name") or f"Annotation {annotation_index + 1}"
        color = normalize_color(annotation_attrs.get("LineColor"))
        regions = annotation.findall(".//Region")
        if not regions:
            warnings.append(f"missing_regions:{annotation_label}")
            continue
        for region_index, region in enumerate(regions):
            record = _record_from_region(
                region,
                annotation_attrs=annotation_attrs,
                annotation_label=annotation_label,
                annotation_index=annotation_index,
                region_index=region_index,
                color=color,
                source=str(source),
                warnings=warnings,
            )
            if record is not None:
                records.append(replace(record, bbox=compute_record_bbox(record)))
    metadata = {
        "microns_per_pixel": root.attrib.get("MicronsPerPixel"),
        "warnings": warnings,
    }
    return AnnotationTable(
        records=records,
        source=str(source),
        source_format="aperio-xml",
        metadata=metadata,
    ).compute_bboxes().normalize_colors()


def _record_from_region(
    region: ET.Element,
    *,
    annotation_attrs: dict[str, str],
    annotation_label: str,
    annotation_index: int,
    region_index: int,
    color: str | None,
    source: str,
    warnings: list[str],
) -> AnnotationRecord | None:
    region_attrs = dict(region.attrib)
    region_id = region_attrs.get("Id") or str(region_index)
    annotation_id = annotation_attrs.get("Id") or str(annotation_index)
    record_id = f"{annotation_id}:{region_id}"
    label = region_attrs.get("Text") or annotation_label
    vertices = _vertices(region)
    if not vertices:
        warnings.append(f"missing_vertices:{record_id}")
        return None
    properties = {"aperio": {"annotation": annotation_attrs, "region": region_attrs}}
    if len(vertices) == 1:
        return AnnotationRecord(
            record_id,
            "point",
            {"x": vertices[0][0], "y": vertices[0][1]},
            label,
            color,
            source=source,
            properties=properties,
        )
    if len(vertices) == 2:
        return AnnotationRecord(record_id, "line", vertices, label, color, source=source, properties=properties)
    return AnnotationRecord(record_id, "polygon", [vertices], label, color, source=source, properties=properties)


def _vertices(region: ET.Element) -> list[tuple[float, float]]:
    vertices: list[tuple[float, float]] = []
    for vertex in region.findall(".//Vertex"):
        try:
            vertices.append((float(vertex.attrib["X"]), float(vertex.attrib["Y"])))
        except (KeyError, ValueError):
            continue
    return vertices
