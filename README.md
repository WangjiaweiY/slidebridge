# SlideBridge Core

A lightweight WSI inspection and debugging toolkit for computational pathology.

Debug whole-slide images like a developer.

![SlideBridge demo overlay](docs/assets/demo_overlay.png)

> The demo image above is synthetic and contains no patient data.

## What is SlideBridge Core?

SlideBridge Core helps computational pathology researchers and AI engineers inspect whole-slide images, normalize metadata, visualize patch coordinates, and generate lightweight QC reports.

Current version: `0.2.0`

## Quick Demo

```powershell
pip install -e .
slidebridge create-demo --out outputs\demo_slide.png
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\demo_overlay.png
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --port 7860 --open-browser
```

## Important Notice

- Research and algorithm development only.
- Not for clinical diagnosis.
- This project does not include proprietary vendor SDKs.
- This project does not include proprietary vendor format implementations.
- Vendor-specific readers should be integrated only through separately licensed private plugins.
- This project is not affiliated with, endorsed by, or certified by any scanner vendor.

## Features

- Unified slide reader interface
- OpenSlide / TiffSlide based public readers
- Metadata inspection
- Thumbnail export
- Local browser-based WSI viewer
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

## Installation on Windows

Create and activate an environment:

```powershell
conda create -n slidebridge python=3.11 -y
conda activate slidebridge
```

Install dependencies and the editable package:

```powershell
pip install tiffslide openslide-python openslide-bin pillow numpy pandas fastapi uvicorn typer rich jinja2 pytest h5py
cd C:\path\to\slidebridge-core
pip install -e .
```

Windows note: `openslide-bin` can provide the OpenSlide DLLs needed by `openslide-python`. If OpenSlide is unavailable, SlideBridge can still run supported workflows through TiffSlide or the image reader where applicable.

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
- `slidebridge render-overlay PATH --patches PATCHES --out OUTPUT`: render a static patch/score overlay image.
- `slidebridge create-demo --out outputs\demo_slide.png`: create a synthetic H&E-like demo image.
- `slidebridge view PATH --patches COORDS.csv --heatmap SCORES.npy`: start the local pan/zoom viewer with optional model/debug score overlay.
- `slidebridge readers`: list registered readers and dependency availability.
- `slidebridge env`: show Python, package, and reader dependency diagnostics.
- `slidebridge version`: show version and runtime information.
- `slidebridge --version`: print the package version.

## Coordinate Convention

- `x` and `y` are level-0 pixel coordinates.
- Patch `width` and `height` are in level-0 pixels unless otherwise stated.
- `Slide.read_region(x, y, width, height, level=0)` uses level-0 `x/y` coordinates.
- Viewer overlays are aligned to level-0 coordinate space.

Patch CSV example:

```csv
x,y,width,height,score
10000,20000,512,512,0.82
```

## Plugin Architecture

The public core defines the reader interface and registry. Private readers should live in separate private packages and register a reader object with `slidebridge.core.registry.register_reader`.

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

- QuPath GeoJSON overlay
- ASAP XML overlay
- annotation conversion

v0.3:

- plugin template
- DICOM WSI optional reader
- OME-TIFF / OME-Zarr optional reader
- better QC metrics

## License

Apache-2.0
