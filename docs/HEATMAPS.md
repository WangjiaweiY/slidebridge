# Heatmaps

SlideBridge heatmaps are model/debug score visualizations. They are not
diagnostic outputs.

SlideBridge supports two heatmap styles:

1. Patch-aligned score heatmaps.
2. Full-slide raster heatmaps from PNG/JPG/JPEG images.

Both are aligned to level-0 slide coordinates for viewing and rendering.

## Patch-Aligned Scores

Scores must align one-to-one with the patch table. If a score file contains `N`
values, the patch coordinate file must contain `N` patches.

Supported score formats:

- CSV with `score`, `attention`, `prob`, `probability`, or `logit`
- NPY with shape `(N,)`, `(N, 1)`, or `(N, C)`
- H5/HDF5 with score datasets such as `scores`, `attention`, `probs`, or `logits`
- PT/PTH when PyTorch is installed

For NPY arrays with shape `(N, C)` and `C > 1`, SlideBridge uses the last
column as the default positive-class/debug score.

Example:

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.h5 --heatmap outputs\attention.npy
```

## Full-Slide Raster Heatmaps

Raster heatmaps are ordinary image files:

- PNG
- JPG
- JPEG

The first implementation assumes the raster heatmap covers the entire slide
extent. The heatmap image is stretched to the full level-0 slide rectangle:

```text
x = 0
y = 0
width = slide level-0 width
height = slide level-0 height
```

This is useful when a model already exported a thumbnail-like heatmap image.
If the heatmap image aspect ratio differs from the slide by more than a small
tolerance, SlideBridge returns a warning but still displays it.

Examples:

```powershell
slidebridge create-demo-heatmap --out outputs\demo_heatmap.png
slidebridge inspect-heatmap outputs\demo_heatmap.png --slide C:\path\to\your\slide.svs
slidebridge view C:\path\to\your\slide.svs --raster-heatmap outputs\demo_heatmap.png
slidebridge view C:\path\to\your\slide.svs --heatmap outputs\heatmap.jpg
```

Useful raster tuning options:

```powershell
slidebridge view C:\path\to\your\slide.svs `
  --raster-heatmap outputs\demo_heatmap.png `
  --raster-heatmap-threshold 0.4 `
  --raster-heatmap-colormap score

slidebridge render-overlay C:\path\to\your\slide.svs `
  --raster-heatmap outputs\demo_heatmap.png `
  --raster-heatmap-invert `
  --out outputs\slide_with_inverted_heatmap.png
```

`--raster-heatmap-threshold` hides pixels below the normalized heatmap value.
`--raster-heatmap-invert` flips normalized intensity before colorization and
thresholding. `--raster-heatmap-colormap` accepts `auto`, `score`,
`grayscale`, or `none`.

Remote example:

```powershell
slidebridge remote-view user@server:/data/slides/case.svs `
  --raster-heatmap /data/model_outputs/case_heatmap.png `
  --remote-runner "conda run -n slidebridge slidebridge"
```

Static rendering:

```powershell
slidebridge render-overlay C:\path\to\your\slide.svs `
  --raster-heatmap outputs\heatmap.png `
  --out outputs\slide_with_heatmap.png
```

Limitations:

- Raster heatmaps are currently treated as full-slide overlays.
- Raster heatmaps do not yet support arbitrary origin/extent metadata.
- Raster heatmaps are not tiled; very large heatmap images are downsampled
  before being served to the browser.
- Raster heatmaps are for research/debugging visualization only.
