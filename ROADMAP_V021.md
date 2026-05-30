# Roadmap v0.2.1

Theme: annotation overlay and conversion.

This is a planning document only. It does not add v0.2.1 code.

## 1. AnnotationTable Abstraction

- polygons
- rectangles
- points
- labels
- colors
- `coordinate_space = "level0"`

## 2. QuPath GeoJSON Loader

- support `Polygon` and `MultiPolygon`
- support classification, name, and color when present
- use level-0 coordinate convention
- do not depend on the QuPath application

## 3. ASAP XML Loader

- support polygon, rectangle, and point annotations
- support group, name, and color when present
- use level-0 coordinate convention

## 4. Viewer Annotation Overlay

- show/hide annotations
- label filter
- opacity controls
- click annotation info

## 5. Static Rendering

- extend `render-overlay` to render annotation overlays
- keep synthetic examples as the default documentation assets

## 6. Conversion Command

Possible command:

```powershell
slidebridge convert-annotations INPUT --out OUTPUT --to slidebridge-json
```

Planned conversions:

- QuPath GeoJSON to SlideBridge JSON
- ASAP XML to SlideBridge JSON
- SlideBridge JSON to GeoJSON

## 7. Tests

- unit tests for loaders
- coordinate convention tests
- viewer API tests
- render-overlay tests
- CLI conversion smoke tests

## 8. Docs

- annotation coordinate convention
- supported public annotation formats
- viewer overlay behavior
- conversion examples using synthetic annotations

## 9. Compliance Wording

- annotations are research/debugging data
- no patient-identifiable data in examples
- not for clinical diagnosis

## Explicit Non-Goals

- no proprietary vendor annotation formats
- no real hospital data integration
- no clinical diagnosis workflow
- no complex web-based annotation editing
