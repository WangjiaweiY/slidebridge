# Annotations

SlideBridge Core uses annotations as research/debugging overlays for algorithm
development workflows.

## Coordinate Convention

- `coordinate_space = "level0"`
- The origin is the top-left corner of the full-resolution image.
- `x` increases to the right.
- `y` increases downward.
- Annotation coordinates are expected to align with slide level-0 pixels.

## Supported Loaders

- QuPath GeoJSON
- ASAP XML
- SlideBridge JSON

Not all vendor-specific or private annotation formats are supported. SlideBridge
Core does not include proprietary annotation format implementations.

## Geometry Types

- polygon
- multipolygon
- rectangle
- point
- line
- unknown

The viewer and static renderer support polygon, rectangle, point, and line
display. Unsupported or malformed geometry is reported as a warning where
possible.

## Research Use

Annotation overlays are for inspection, debugging, and algorithm development.
They are not clinical diagnosis tools.
