# Figure Rendering

`slidebridge render-figure` exports a static, publication-style debug figure
without opening a browser.

The command is intended for research and algorithm debugging figures. It is not
for clinical diagnosis.

## Basic Usage

```powershell
slidebridge render-figure outputs\demo_slide.png `
  --out outputs\figure.png `
  --center-x 2048 --center-y 1536 `
  --window-width 1600 --window-height 1200 `
  --title "Model output overview" `
  --panel-label A
```

## With Raster Heatmap And Insets

```powershell
slidebridge render-figure outputs\demo_slide.png `
  --raster-heatmap outputs\demo_heatmap.png `
  --inset-x 1800 --inset-y 1300 `
  --inset-width 512 --inset-height 512 `
  --title "Raster heatmap overview" `
  --panel-label A `
  --scalebar-um 500 `
  --mpp 0.25 `
  --out outputs\figure_heatmap.png
```

If `--inset-heatmap` is omitted, the inset heatmap panel uses the same image as
`--raster-heatmap`. Use `--no-inset-heatmap-panel` to export only the raw inset
patch.

## Coordinate Convention

- `--center-x` and `--center-y` are level-0 pixel coordinates for the main view.
- `--window-width` and `--window-height` are level-0 pixels.
- `--inset-x` and `--inset-y` are the level-0 top-left coordinates of the inset.
- `--inset-width` and `--inset-height` are level-0 pixels.
- Full-slide raster heatmaps are stretched to the level-0 slide coordinate
  space, matching the viewer behavior.

## Scale Bar

`--scalebar-um` draws a micron scale bar on the main panel. SlideBridge uses
slide MPP metadata when available. If the slide does not have MPP metadata,
provide `--mpp`.

## Limitations

- The first version supports a single main panel plus optional inset patch and
  inset heatmap panels.
- It does not perform automatic figure layout optimization for every journal.
- It does not add diagnostic meaning to heatmaps or annotations.
