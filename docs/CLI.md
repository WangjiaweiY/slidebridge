# SlideBridge CLI Reference

This page collects command-line examples for users who prefer terminal workflows or need automation. The main README focuses on the browser workflow.

All paths below are generic examples. Replace them with your own slide, heatmap, patch, and annotation paths.

## Command Invocation

If the console script is available:

```cmd
slidebridge version
```

If `slidebridge` is not on `PATH`, use the Python module form:

```cmd
python -m slidebridge.cli version
```

On Windows with Conda, you can also call the environment Python directly:

```cmd
%CONDA_PREFIX%\python.exe -m slidebridge.cli version
```

PowerShell uses the backtick `` ` `` for multi-line commands. Anaconda Prompt and `cmd` do not; use single-line commands there.

## Web App

```cmd
slidebridge app
```

```cmd
python -m slidebridge.cli app
```

## Remote Viewer Over SSH

Remote slides stay on the server. The local browser connects through an SSH tunnel.

```cmd
slidebridge remote-view user@server:/data/slides/case.svs --remote-runner "/home/user/miniconda3/envs/slidebridge/bin/python -m slidebridge.cli"
```

Non-22 SSH port:

```cmd
slidebridge remote-view user@server:/data/slides/case.svs --ssh-port 2222 --remote-runner "/home/user/miniconda3/envs/slidebridge/bin/python -m slidebridge.cli"
```

Open a directory and choose slides in the browser:

```cmd
slidebridge remote-view user@server:/data/slides --max-slides 500 --remote-runner "/home/user/miniconda3/envs/slidebridge/bin/python -m slidebridge.cli"
```

Remote viewers started by `remote-view` use a heartbeat lease. If the local launcher or SSH tunnel disappears, the remote viewer exits after the idle timeout.

```cmd
slidebridge remote-view user@server:/data/slides --remote-idle-timeout 120 --remote-runner "/home/user/miniconda3/envs/slidebridge/bin/python -m slidebridge.cli"
```

## Local Viewer

```cmd
slidebridge view outputs\demo_slide.png --open-browser
```

Raster heatmap:

```cmd
slidebridge view outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --open-browser
```

Multiple raster heatmap layers:

```cmd
slidebridge view outputs\demo_slide.png --raster-heatmap-layer low=outputs\heatmap_low.png --raster-heatmap-layer high=outputs\heatmap_high.png --open-browser
```

Patch coordinates and annotations:

```cmd
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.csv --annotations outputs\demo_annotations.geojson --open-browser
```

## Synthetic Demo Data

```cmd
slidebridge create-demo --out outputs\demo_slide.png
slidebridge create-demo-heatmap --out outputs\demo_heatmap.png --slide outputs\demo_slide.png
slidebridge create-demo-annotations --out outputs\demo_annotations.geojson
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv --count 200 --with-scores
```

## Inspection And QC

```cmd
slidebridge inspect outputs\demo_slide.png
slidebridge thumbnail outputs\demo_slide.png --out outputs\demo_thumbnail.jpg
slidebridge doctor outputs\demo_slide.png --out outputs\demo_report.html --json-out outputs\demo_report.json
```

## Patch Tools

```cmd
slidebridge inspect-patches outputs\demo_coords.csv --slide outputs\demo_slide.png
slidebridge export-patches outputs\demo_slide.png --patches outputs\demo_coords.csv --out outputs\patches --limit 20
```

## Heatmap Debugging

Patch score or attention overlays:

```cmd
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.h5 --format h5 --count 200 --with-scores
slidebridge view outputs\demo_slide.png --patches outputs\demo_coords.h5 --port 7860 --open-browser
```

Full-slide PNG/JPG heatmap:

```cmd
slidebridge inspect-heatmap outputs\demo_heatmap.png --slide outputs\demo_slide.png
slidebridge render-overlay outputs\demo_slide.png --raster-heatmap outputs\demo_heatmap.png --out outputs\demo_raster_heatmap.png
```

## Static Rendering

Render a fixed viewport:

```cmd
slidebridge render-view outputs\demo_slide.png --center-x 4000 --center-y 3000 --window-width 2000 --out outputs\view.png
```

Render a publication figure from a JSON spec:

```cmd
slidebridge render-figure outputs\demo_slide.png --spec outputs\figure_spec.json --out outputs\figure.png
```

## Annotation Formats

See:

- [Annotation formats](ANNOTATION_FORMATS.md)
- [Annotations](ANNOTATIONS.md)
- [Coordinates](COORDINATES.md)
- [Heatmaps](HEATMAPS.md)
- [Export patches](EXPORT_PATCHES.md)
