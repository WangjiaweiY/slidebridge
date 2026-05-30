from __future__ import annotations

from slidebridge.annotations.asap import load_asap_xml


def test_asap_polygon_group_label_and_color(tmp_path):
    path = tmp_path / "annotations.xml"
    path.write_text(
        """<?xml version="1.0"?>
<ASAP_Annotations>
  <Annotations>
    <Annotation Name="a" Type="Polygon" PartOfGroup="Tumor" Color="">
      <Coordinates>
        <Coordinate Order="0" X="0" Y="0"/>
        <Coordinate Order="1" X="10" Y="0"/>
        <Coordinate Order="2" X="10" Y="10"/>
        <Coordinate Order="3" X="0" Y="10"/>
      </Coordinates>
    </Annotation>
  </Annotations>
  <AnnotationGroups>
    <Group Name="Tumor" Color="#ff0000"/>
  </AnnotationGroups>
</ASAP_Annotations>
""",
        encoding="utf-8",
    )

    table = load_asap_xml(path)

    assert len(table) == 1
    assert table.records[0].type == "polygon"
    assert table.records[0].label == "Tumor"
    assert table.records[0].color == "#ff0000"


def test_asap_rectangle_and_point(tmp_path):
    path = tmp_path / "annotations.xml"
    path.write_text(
        """<ASAP_Annotations><Annotations>
<Annotation Name="r" Type="Rectangle" PartOfGroup="Stroma" Color="#00ff00"><Coordinates>
<Coordinate Order="0" X="10" Y="20"/><Coordinate Order="1" X="30" Y="40"/>
</Coordinates></Annotation>
<Annotation Name="p" Type="Dot" PartOfGroup="Point" Color="#0000ff"><Coordinates>
<Coordinate Order="0" X="5" Y="6"/>
</Coordinates></Annotation>
</Annotations></ASAP_Annotations>""",
        encoding="utf-8",
    )

    table = load_asap_xml(path)

    assert [record.type for record in table.records] == ["rectangle", "point"]
    assert table.records[0].coordinates["width"] == 20.0


def test_asap_missing_coordinates_warning(tmp_path):
    path = tmp_path / "annotations.xml"
    path.write_text(
        """<ASAP_Annotations><Annotations>
<Annotation Name="empty" Type="Polygon" PartOfGroup="Tumor" Color="#ff0000"><Coordinates /></Annotation>
</Annotations></ASAP_Annotations>""",
        encoding="utf-8",
    )

    table = load_asap_xml(path)

    assert len(table) == 0
    assert "missing_coordinates:empty" in table.summary()["warnings"]
