# Heatmaps

SlideBridge heatmaps are model/debug score visualizations. They are not diagnostic outputs.

Scores must align one-to-one with the patch table. If a score file contains `N` values, the patch coordinate file must contain `N` patches.

Supported score formats:

- CSV with `score`, `attention`, `prob`, `probability`, or `logit`
- NPY with shape `(N,)`, `(N, 1)`, or `(N, C)`
- H5/HDF5 with score datasets such as `scores`, `attention`, `probs`, or `logits`
- PT/PTH when PyTorch is installed

For NPY arrays with shape `(N, C)` and `C > 1`, SlideBridge uses the last column as the default positive-class/debug score.

Example:

```powershell
slidebridge view C:\path\to\your\slide.svs --patches outputs\coords.h5 --heatmap outputs\attention.npy
```

