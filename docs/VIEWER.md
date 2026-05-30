# Viewer

The viewer command starts a local FastAPI tile server and opens a browser-based OpenSeadragon viewer:

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.csv --port 7860 --open-browser
```

The tile server is intended for local research and development workflows.

## OpenSeadragon

v0.1.1 loads OpenSeadragon from a CDN. If the CDN asset cannot load, the page shows a clear message instead of staying blank.

## Patch Overlay

Patch overlays come from CSV rows with level-0 coordinates:

```csv
x,y,width,height,score
10000,20000,512,512,0.82
```

If more than 10000 patches are provided, the viewer displays a warning and renders the first 10000 rectangles to keep the browser responsive.

## Tile Options

```powershell
slidebridge view C:\path\to\your\slide.svs --tile-size 256 --jpeg-quality 85
```

Tiles are JPEG responses with a one-hour cache header.

