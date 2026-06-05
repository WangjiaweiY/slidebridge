from __future__ import annotations

from slidebridge.annotations.aperio import load_aperio_xml
from slidebridge.annotations.io import load_annotation_table


APERIO_XML = """<?xml version='1.0' encoding='utf-8'?>
<Annotations MicronsPerPixel="0.25">
  <Annotation Id="1" Name="main" LineColor="65280" Type="4">
    <Regions>
      <Region Id="1" Text="tumor" Type="0">
        <Vertices>
          <Vertex X="10" Y="20" Z="0" />
          <Vertex X="30" Y="20" Z="0" />
          <Vertex X="30" Y="50" Z="0" />
          <Vertex X="10" Y="50" Z="0" />
        </Vertices>
      </Region>
    </Regions>
  </Annotation>
</Annotations>
"""


def test_load_aperio_xml_polygon(tmp_path):
    path = tmp_path / "aperio.xml"
    path.write_text(APERIO_XML, encoding="utf-8")

    table = load_aperio_xml(path)

    assert table.source_format == "aperio-xml"
    assert len(table) == 1
    assert table.records[0].type == "polygon"
    assert table.records[0].label == "tumor"
    assert table.records[0].color == "#00ff00"
    assert table.records[0].bbox == (10.0, 20.0, 30.0, 50.0)
    assert table.metadata["microns_per_pixel"] == "0.25"


def test_load_annotation_table_auto_detects_aperio_xml(tmp_path):
    path = tmp_path / "annotations.xml"
    path.write_text(APERIO_XML, encoding="utf-8")

    table = load_annotation_table(path)

    assert table.source_format == "aperio-xml"
    assert len(table) == 1
