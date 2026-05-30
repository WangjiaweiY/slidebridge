# Viewer

The viewer command starts a local FastAPI tile server and opens a browser-based
OpenSeadragon viewer:

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.csv --port 7860 --open-browser
```

The tile server is intended for local research and development workflows.

## OpenSeadragon

The viewer first loads the bundled OpenSeadragon asset from the installed
SlideBridge package. If the local asset cannot load, it falls back to the
OpenSeadragon CDN. If both fail, the page shows a clear message instead of
staying blank.

## Patch Overlay

Patch overlays come from CSV rows with level-0 coordinates:

```csv
x,y,width,height,score
10000,20000,512,512,0.82
```

If more than 10000 patches are provided, the viewer displays a warning and
renders the first 10000 rectangles to keep the browser responsive.

## Heatmap Overlay

If patches include `score` or `attention`, or if `--heatmap` is provided, the
viewer renders a model/debug score overlay.

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.h5 --heatmap outputs\attention.npy --heatmap-opacity 0.45
```

The viewer includes:

- show/hide overlay toggle
- opacity slider
- score legend
- patch count
- hover text with index, coordinates, size, and score

For large overlays, the server can limit returned patches with
`--max-overlay-patches`, and the browser displays a performance warning.

## Annotation Overlay

The viewer can display annotation files with patch and heatmap overlays:

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.csv --annotations outputs\annotations.geojson --port 7860 --open-browser
```

Annotation overlays use level-0 image coordinates and support:

- show/hide toggle
- opacity slider
- label summary
- hover text with label, type, id, and bbox
- polygon, rectangle, point, and line display

If the annotation count exceeds `--max-annotations`, the server returns the
first subset and reports a warning.

## Tile Options

```powershell
slidebridge view C:\path\to\your\slide.svs --tile-size 256 --jpeg-quality 85
```

Tiles are JPEG responses with a one-hour cache header.
