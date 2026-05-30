# Annotation Formats

## QuPath GeoJSON

SlideBridge can load GeoJSON `FeatureCollection`, a single `Feature`, a feature
list, and common object-array exports. Supported geometry includes `Polygon`,
`MultiPolygon`, `Point`, `MultiPoint`, `LineString`, and expandable
`GeometryCollection`.

Label extraction order:

- `properties.classification.name`
- `properties.name`
- `properties.pathClass`
- `properties.objectType`

Color extraction supports integer color values and `#RRGGBB` strings.

## ASAP XML

SlideBridge can load common ASAP XML annotations with:

- `Polygon`
- `Rectangle`
- `Dot` / `Point`
- `Line`
- `Spline` approximated as line with a warning

Label extraction order:

- `PartOfGroup`
- `Name`
- `Type`

Color extraction uses annotation color first, then group color.

## SlideBridge JSON

SlideBridge JSON is the normalized interchange format:

```json
{
  "type": "SlideBridgeAnnotationTable",
  "version": "0.2.1",
  "coordinate_space": "level0",
  "metadata": {},
  "annotations": []
}
```

Use `slidebridge convert-annotations` to write SlideBridge JSON or GeoJSON.
