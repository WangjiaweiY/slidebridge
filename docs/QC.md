# QC

SlideBridge Core provides lightweight QC signals for debugging and research
workflows.

## Tissue Percent

`tissue_percent` is a heuristic computed from a thumbnail using brightness and
saturation thresholds. It is useful for quick inspection, not for diagnosis.

## Blur Score

`blur_score` is a simple Laplacian variance score computed with NumPy. A very
low value can indicate possible blur, but thresholds are intentionally
conservative.

These QC values are not clinical or diagnostic metrics.
