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

Patch overlays are drawn on a browser canvas instead of one DOM node per patch.
During pan and zoom the viewer culls records outside the current viewport and
draws only visible items. The overlay panel reports how many records were drawn
on the current canvas frame.

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
- canvas draw count
- score threshold filtering
- top-k patch filtering
- click-to-inspect patch details and zoom-to-item

For large overlays, the server can limit returned patches with
`--max-overlay-patches`, and the browser displays a performance warning.

## Raster Heatmap Overlay

The viewer can also display a full-slide PNG/JPG/JPEG heatmap:

```powershell
slidebridge view C:\path\to\your\slide.svs --raster-heatmap outputs\heatmap.png --heatmap-opacity 0.45
slidebridge inspect-heatmap outputs\heatmap.png --slide C:\path\to\your\slide.svs
```

If `--heatmap` points to a PNG/JPG/JPEG file, SlideBridge treats it as a raster
heatmap automatically:

```powershell
slidebridge view C:\path\to\your\slide.svs --heatmap outputs\heatmap.jpg
```

Raster heatmaps are stretched over the full level-0 slide extent. If the aspect
ratio differs from the slide, the viewer reports a warning. Raster heatmaps are
model/debug visualizations only.

Optional raster controls:

- `--raster-heatmap-threshold 0.4` hides lower normalized values.
- `--raster-heatmap-invert` flips normalized intensity before display.
- `--raster-heatmap-colormap score` forces the SlideBridge score colormap.

## Static View Snapshots

Use `render-view` when you want a reproducible viewport image without opening a
browser. The command reads a level-0 window around a requested center point,
rescales it to a fixed output size, and draws the same debug overlays used by
the viewer:

```powershell
slidebridge render-view C:\path\to\your\slide.svs `
  --patches outputs\coords.csv `
  --annotations outputs\annotations.geojson `
  --raster-heatmap outputs\heatmap.png `
  --center-x 50000 --center-y 30000 `
  --window-width 4000 --window-height 3000 `
  --out outputs\viewport.png
```

All viewport coordinates are level-0 pixels. `--window-width` and
`--window-height` define the field of view in level-0 pixels. `--out-width` and
`--out-height` define the exported image size. This is useful for reports,
debugging screenshots, and comparing model outputs without relying on browser
state.

## Annotation Overlay

The viewer can display annotation files with patch and heatmap overlays:

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.csv --annotations outputs\annotations.geojson --port 7860 --open-browser
```

The overlay panel can filter annotations by label. Label filters are applied in
the browser to the records already returned by `/api/annotations`; they do not
modify annotation files and are only for research/debugging inspection.

Annotation overlays use level-0 image coordinates and support:

- show/hide toggle
- opacity slider
- label summary
- hover text with label, type, id, and bbox
- polygon, rectangle, point, and line display
- canvas viewport culling

If the annotation count exceeds `--max-annotations`, the server returns the
first subset and reports a warning.

## Tile Options

```powershell
slidebridge view C:\path\to\your\slide.svs --tile-size 256 --jpeg-quality 85 --tile-cache-size 512 --tile-cache-mb 256 --tile-workers 4
```

Tiles use a per-viewer cache key so restarting the viewer on the same localhost
port does not mix old and new slide images. HTML, DZI, and overlay APIs use
`Cache-Control: no-store`; keyed tile images can be cached for repeated
navigation inside the same viewer session.

`--tile-cache-size` controls the maximum number of cached JPEG tile responses.
Use `--tile-cache-size 0` to disable the server-side tile cache. The cache is
per-process and disappears when the viewer stops.

`--tile-cache-mb` adds a byte-aware cache limit. The cache evicts least recently
used tiles when either the tile count or memory limit is exceeded.

`--tile-workers` limits how many tiles can be generated concurrently. This helps
avoid CPU spikes when OpenSeadragon requests many tiles during fast zooming or
panning.

The viewer information panel, `/api/cache-stats`, and `/api/performance` expose:

- cache enabled state
- entries and max entries
- cache memory and max MB
- hits and misses
- evictions
- tile worker limit
- generated tiles and cache-served tiles
- average and p95 tile generation time
- read, resize, JPEG encode, and total tile timing summaries
