# SlideBridge Core

[![CI](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml/badge.svg)](https://github.com/WangjiaweiY/slidebridge/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

[中文 README](README.md)

A lightweight WSI inspection and debugging toolkit for computational pathology.

Debug whole-slide images like a developer.

![SlideBridge demo overlay](docs/assets/demo_overlay.png)

> The demo image above is synthetic and contains no patient data.

## What is SlideBridge Core?

SlideBridge Core helps computational pathology researchers and AI engineers
inspect whole-slide images, normalize metadata, visualize patch coordinates, and
generate lightweight QC reports.

Current version: `0.2.17`

## Quick Demo

```powershell
git clone https://github.com/WangjiaweiY/slidebridge.git
cd slidebridge
pip install -e .
slidebridge create-demo --out outputs\demo_slide.png
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\demo_overlay.png
slidebridge render-view outputs\demo_slide.png --patches outputs\demo_coords.csv --center-x 2048 --center-y 1536 --window-width 1200 --window-height 900 --out outputs\demo_view.png
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --port 7860 --open-browser
```

## Important Notice

- Research and algorithm development only.
- Not for clinical diagnosis.
- This project does not include proprietary vendor SDKs.
- This project does not include proprietary vendor format implementations.
- Vendor-specific readers should be integrated only through separately licensed
  private plugins.
- This project is not affiliated with, endorsed by, or certified by any scanner
  vendor.

## Features

- Unified slide reader interface
- OpenSlide / TiffSlide based public readers
- Metadata inspection
- Thumbnail export
- Local browser-based WSI viewer
- Bundled local OpenSeadragon viewer asset with CDN fallback
- Patch coordinate overlay
- Lightweight QC report
- Plugin-friendly architecture
- Environment and reader diagnostics
- Synthetic demo image generation
- PatchTable coordinate abstraction
- CSV/NPY/H5/JSON/PT optional coordinate loading
- Score/attention heatmap overlay
- Patch image export
- Static overlay rendering
- Static viewport rendering with `render-view`
- AnnotationTable abstraction
- QuPath GeoJSON, ASAP XML, and SlideBridge JSON annotation loading
- Annotation overlay, conversion, and patch labeling
- Remote WSI viewing over SSH tunnel

## Installation

### From GitHub

```powershell
pip install git+https://github.com/WangjiaweiY/slidebridge.git
```

### Development Install

```powershell
git clone https://github.com/WangjiaweiY/slidebridge.git
cd slidebridge
pip install -e .[dev]
```

## Windows Notes

Create and activate an environment:

```powershell
conda create -n slidebridge python=3.11 -y
conda activate slidebridge
```

If you are setting up a fresh Windows environment, install dependencies first:

```powershell
pip install tiffslide openslide-python openslide-bin pillow numpy pandas fastapi uvicorn typer rich jinja2 pytest h5py
pip install -e .
```

Windows note: `openslide-bin` can provide the OpenSlide DLLs needed by
`openslide-python`. If OpenSlide is unavailable, SlideBridge can still run
supported workflows through TiffSlide or the image reader where applicable.

## Quick Start with Synthetic Demo

```powershell
slidebridge create-demo --out outputs\demo_slide.png
slidebridge inspect outputs\demo_slide.png
slidebridge thumbnail outputs\demo_slide.png --out outputs\demo_thumbnail.jpg
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --patch-size 256 --count 100
slidebridge doctor outputs\demo_slide.png --out outputs\demo_report.html
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --port 7860 --open-browser
```

## Model Output Debugging

Generate coordinates in an interoperable H5 format and inspect model/debug scores in the viewer:

```powershell
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.h5 --format h5 --count 200
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.h5 --port 7860 --open-browser
```

## Attention / Score Heatmap

If the coordinate file contains `score` or `attention`, SlideBridge can render a model/debug score overlay:

```powershell
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\demo_overlay.png
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --port 7860 --open-browser
```

If scores are stored separately:

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.h5 --heatmap outputs\attention.npy
```

## Full-Slide Heatmap PNG/JPG

If a model exports a whole-image PNG/JPG heatmap, use it as a full-slide overlay:

```powershell
slidebridge create-demo-heatmap --out outputs\demo_heatmap.png
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --port 7860 --open-browser
slidebridge inspect-heatmap outputs\demo_heatmap.png --slide outputs\demo_slide.png
```

`--heatmap` also auto-detects image heatmaps:

```powershell
slidebridge render-overlay outputs\demo_slide.png --heatmap outputs\demo_heatmap.png --out outputs\demo_raster_heatmap.png
```

Raster heatmaps currently cover the full slide extent and are stretched to the
level-0 coordinate space. They are model/debug visualizations, not diagnostic
outputs.

Multiple full-slide heatmaps can be loaded as independent layers:

```powershell
slidebridge view outputs\demo_slide.png `
  --raster-heatmap-layer low=outputs\heatmap_low.png `
  --raster-heatmap-layer high=outputs\heatmap_high.png `
  --port 7860 --open-browser
```

Useful tuning options:

```powershell
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --raster-heatmap-threshold 0.4 --raster-heatmap-colormap score
slidebridge render-overlay outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --raster-heatmap-invert --out outputs\demo_raster_heatmap.png
```

## Static View Snapshots

Use `render-view` to export a reproducible viewport snapshot without opening a
browser:

```powershell
slidebridge render-view outputs\demo_slide.png `
  --patches outputs\demo_coords.csv `
  --annotations outputs\demo_annotations.geojson `
  --raster-heatmap outputs\demo_heatmap.png `
  --center-x 2048 --center-y 1536 `
  --window-width 1200 --window-height 900 `
  --out outputs\demo_view.png
```

The viewer information panel can also copy a `render-view` command for the
current viewport or download the current viewport as a PNG.
It can also copy a viewer URL that restores the selected slide, viewport, panel,
overlay toggles, and overlay filters after refresh.

## Annotation Debugging

Use synthetic annotations to test the annotation workflow without patient data:

```powershell
slidebridge create-demo --out outputs\demo_slide.png
slidebridge create-demo-annotations --out outputs\demo_annotations.geojson
slidebridge inspect-annotations outputs\demo_annotations.geojson --slide outputs\demo_slide.png
slidebridge render-overlay outputs\demo_slide.png --annotations outputs\demo_annotations.geojson --out outputs\demo_annotation_overlay.png
slidebridge view outputs\demo_slide.png --annotations outputs\demo_annotations.geojson --port 7860 --open-browser
```

SlideBridge Core can load QuPath GeoJSON, ASAP XML, and SlideBridge JSON
annotations. Annotation coordinates use level-0 image pixels.

## Label Patches from Annotations

Annotation-based patch labeling is a debugging and weak-labeling helper. It is
not a clinical or gold-standard labeling workflow.

```powershell
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge label-patches outputs\demo_coords.csv --annotations outputs\demo_annotations.geojson --out outputs\demo_coords_labeled.csv
```

## Remote WSI Viewing over SSH

View slides stored on a remote server from your local browser. The slide remains
on the server; SlideBridge runs the tile server remotely and forwards it to
localhost over SSH.

```powershell
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "conda run -n slidebridge slidebridge"
```

You can also pass a remote directory and choose slides in the browser:

```powershell
slidebridge remote-view user@server:/data/slides --recursive --max-slides 500 --remote-runner "conda run -n slidebridge slidebridge"
```

With remote patch coordinates and annotations:

```powershell
slidebridge remote-view user@server:/data/slides/case.svs `
  --patches /data/features/case_coords.h5 `
  --annotations /data/annotations/case.geojson `
  --remote-runner "conda run -n slidebridge slidebridge"
```

Use `slidebridge remote-view --dry-run` to inspect the SSH tunnel and remote
command before connecting. See [Remote WSI Viewing](docs/REMOTE_VIEWING.md).

For repeated use, save a local remote profile once and reuse shorter commands:

```powershell
slidebridge remote-profile add lab `
  --host server.example.org `
  --user user `
  --ssh-port 22 `
  --remote-runner "conda run -n slidebridge slidebridge" `
  --root /data/slides

slidebridge remote-view lab:case.svs
slidebridge remote-view lab:cohort-a/ --recursive
slidebridge remote-ls lab:
```

## Viewer Performance Options

The viewer enables an in-process tile cache by default and limits concurrent
tile generation to reduce server pressure during repeated zooming and panning:

```powershell
slidebridge view outputs\demo_slide.png --tile-cache-size 512 --tile-cache-mb 256 --tile-workers 4
slidebridge remote-view user@server:/data/slides/case.svs --tile-cache-size 512 --tile-cache-mb 256 --tile-workers 4
```

Use `--tile-cache-size 0` to disable the server-side tile cache. The viewer info
panel shows cache entries, memory use, hits, misses, evictions, generated tiles,
cache-served tiles, and average/p95 tile generation time.

## Export Patches

```powershell
slidebridge export-patches C:\path\to\your\slide.svs --patches outputs\coords.csv --out outputs\patches --limit 50
```

## Use Your Own WSI

```bat
set SLIDE=C:\path\to\your\slide.svs

slidebridge inspect "%SLIDE%"
slidebridge thumbnail "%SLIDE%" --out outputs\thumbnail.jpg --max-size 2048
slidebridge doctor "%SLIDE%" --out outputs\qc_report.html
slidebridge sample-patches "%SLIDE%" --out outputs\coords.csv --patch-size 512 --count 100
slidebridge view "%SLIDE%" --patches outputs\coords.csv --port 7860 --open-browser
```

## CLI Commands

- `slidebridge inspect PATH`: inspect reader, dimensions, levels, MPP, objective, vendor, metadata, and warnings.
- `slidebridge thumbnail PATH --out OUTPUT`: export an RGB thumbnail.
- `slidebridge doctor PATH_OR_DIR --out REPORT.html --json-out REPORT.json`: generate HTML and optional JSON QC reports.
- `slidebridge sample-patches PATH --out COORDS.csv`: create random patch coordinates for overlay testing.
- `slidebridge inspect-patches PATCHES --slide PATH`: inspect coordinate files and optional slide bounds.
- `slidebridge export-patches PATH --patches PATCHES --out DIR`: export patch images and a manifest.
- `slidebridge render-overlay PATH --patches PATCHES --annotations ANNOTATIONS --out OUTPUT`: render a static overlay image.
- `slidebridge create-demo --out outputs\demo_slide.png`: create a synthetic H&E-like demo image.
- `slidebridge create-demo-heatmap --out outputs\demo_heatmap.png`: create a synthetic raster heatmap.
- `slidebridge create-demo-annotations --out outputs\demo_annotations.geojson`: create synthetic demo annotations.
- `slidebridge inspect-annotations ANNOTATIONS --slide PATH`: inspect annotation files and optional slide bounds.
- `slidebridge convert-annotations INPUT --out OUTPUT`: convert public annotation formats.
- `slidebridge label-patches PATCHES --annotations ANNOTATIONS --out OUTPUT`: assign annotation-derived patch labels.
- `slidebridge remote-check REMOTE`: check remote SSH and SlideBridge availability.
- `slidebridge remote-ls REMOTE_DIR`: list likely slide files on a remote server.
- `slidebridge remote-inspect REMOTE_SLIDE`: inspect a remote slide over SSH.
- `slidebridge remote-view REMOTE_SLIDE_OR_DIR`: view a remote slide or slide directory through an SSH localhost tunnel.
- `slidebridge remote-profile add/list/show/remove`: manage reusable local SSH viewer profiles.
- `slidebridge view PATH --patches COORDS.csv --heatmap SCORES.npy`: start the
  local pan/zoom viewer with optional model/debug score and annotation overlays.
- `slidebridge readers`: list registered readers and dependency availability.
- `slidebridge env`: show Python, package, and reader dependency diagnostics.
- `slidebridge version`: show version and runtime information.
- `slidebridge --version`: print the package version.

## Engineering Notes

Known issues, fixes, and planned improvements are tracked in
[Issues and Improvements](docs/ISSUES_AND_IMPROVEMENTS.md).

## Coordinate Convention

- `x` and `y` are level-0 pixel coordinates.
- Patch `width` and `height` are in level-0 pixels unless otherwise stated.
- `Slide.read_region(x, y, width, height, level=0)` uses level-0 `x/y` coordinates.
- Viewer overlays are aligned to level-0 coordinate space.
- Annotation overlays are also aligned to level-0 coordinate space.

Patch CSV example:

```csv
x,y,width,height,score
10000,20000,512,512,0.82
```

## Plugin Architecture

The public core defines the reader interface and registry. Private readers
should live in separate private packages and register a reader object with
`slidebridge.core.registry.register_reader`.

Minimal fake reader sketch:

```python
from slidebridge.core.registry import register_reader


class FakeReader:
    name = "fake"
    priority = 1

    def can_open(self, path):
        return False

    def open(self, path):
        raise RuntimeError("FakeReader is only an example.")


register_reader(FakeReader())
```

No proprietary reader is included in SlideBridge Core.

## Roadmap

v0.2.0:

- interoperable patch coordinate loading
- model/debug score heatmap overlay
- patch image export
- patch coordinate inspection

v0.2.1:

- annotation overlay
- QuPath GeoJSON overlay
- ASAP XML overlay
- annotation conversion
- patch labeling from annotations

v0.2.2:

- remote WSI viewing over SSH tunnel
- remote-check, remote-ls, remote-inspect, and remote-view
- dry-run remote command diagnostics
- local and remote directory viewer mode

v0.2.3:

- PNG/JPG full-slide raster heatmap overlay
- `--raster-heatmap` support for `view`, `remote-view`, and `render-overlay`
- viewer tile/API cache hardening

v0.2.4:

- in-memory LRU tile cache
- tile generation concurrency limit
- viewer cache stats diagnostics

v0.2.5:

- byte-aware tile cache limit with `--tile-cache-mb`
- tile performance metrics through `/api/performance`
- viewer timing diagnostics for read/resize/JPEG/total tile generation

v0.2.6:

- reusable remote profiles for SSH viewer settings
- profile-relative remote paths for shorter commands

v0.2.7:

- canvas overlay rendering
- viewport culling for large patch and annotation overlays
- overlay draw count and canvas tooltip

v0.2.8:

- heatmap inspection command
- raster heatmap threshold / invert / colormap controls
- slide-aspect synthetic heatmap generation

v0.2.9:

- viewer-side score threshold and top-k patch filters
- annotation label filters
- click-to-inspect overlay details and zoom-to-item

v0.2.10:

- static viewport snapshots with `render-view`
- viewport-level patch / heatmap / annotation overlay export

v0.2.11:

- copy current viewer viewport as a reproducible `render-view` command
- download current viewer viewport as a PNG

v0.2.12:

- shareable viewer URLs for selected slide, viewport, panel, and overlay filters
- refresh-safe viewer state restoration

v0.2.13:

- restrained glassmorphism viewer styling
- Playwright viewer visual and interaction regression tests

v0.3:

- plugin template

## License

Apache-2.0
