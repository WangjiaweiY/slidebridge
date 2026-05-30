# Coordinates

SlideBridge uses level-0 slide coordinates as the default coordinate space.

- `x` and `y` are level-0 pixel coordinates.
- Patch `width` and `height` are level-0 pixels unless otherwise stated.
- `read_region(x, y, width, height, level=0)` uses level-0 `x/y`.
- Viewer overlays are aligned to level-0 image coordinates.

Patch CSV format:

```csv
x,y,width,height,score
10000,20000,512,512,0.82
```

Required columns: `x`, `y`.

Optional columns: `width`, `height`, `score`.

If `width` or `height` is missing, SlideBridge uses `256`.
