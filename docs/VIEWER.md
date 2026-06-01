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

## Raster Heatmap Overlay

The viewer can also display a full-slide PNG/JPG/JPEG heatmap:

```powershell
slidebridge view C:\path\to\your\slide.svs --raster-heatmap outputs\heatmap.png --heatmap-opacity 0.45
```

If `--heatmap` points to a PNG/JPG/JPEG file, SlideBridge treats it as a raster
heatmap automatically:

```powershell
slidebridge view C:\path\to\your\slide.svs --heatmap outputs\heatmap.jpg
```

Raster heatmaps are stretched over the full level-0 slide extent. If the aspect
ratio differs from the slide, the viewer reports a warning. Raster heatmaps are
model/debug visualizations only.

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

Tiles use a per-viewer cache key so restarting the viewer on the same localhost
port does not mix old and new slide images. HTML, DZI, and overlay APIs use
`Cache-Control: no-store`; keyed tile images can be cached for repeated
navigation inside the same viewer session.
