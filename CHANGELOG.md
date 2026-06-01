# Changelog

## 0.2.4

Added:

- in-memory LRU tile cache for the browser viewer
- tile generation concurrency limit for local and remote viewers
- `/api/cache-stats` endpoint for viewer cache diagnostics
- `--tile-cache-size` and `--tile-workers` options for `view` and `remote-view`

Changed:

- OpenSeadragon defaults now limit image loading concurrency and browser-side cache pressure
- viewer information panel displays tile cache entries, hits, misses, evictions, and workers

## 0.2.3

Added:

- Full-slide raster heatmap overlay from PNG/JPG/JPEG images
- `--raster-heatmap` option for `view`, `remote-view`, and `render-overlay`
- automatic raster heatmap detection when `--heatmap` points to PNG/JPG/JPEG

Changed:

- viewer overlay APIs and DZI/tile URLs use explicit no-cache/session keys to avoid stale overlays and tiles
- GitHub default README is Chinese, with English README available separately

Compliance:

- raster heatmaps are model/debug visualizations only
- no clinical diagnosis workflow is added

## 0.2.2

Added:

- Remote WSI viewing over SSH tunnel
- remote-view command
- remote-check command
- remote-ls command
- remote-inspect command
- remote command builder utilities
- directory viewer mode for local and remote slide folders
- redesigned browser viewer shell with slide library selection
- docs for remote viewing from Windows to Linux servers

Security/Compliance:

- remote viewer binds to 127.0.0.1 by default
- no slide data is downloaded automatically
- no proprietary readers or vendor SDKs
- research/debugging only

## 0.2.1

Added:

- AnnotationTable abstraction
- QuPath GeoJSON annotation loading
- ASAP XML annotation loading
- SlideBridge JSON annotation format
- annotation inspection command
- annotation overlay in viewer
- static annotation rendering
- annotation conversion
- patch labeling from annotations

Compliance:

- no proprietary annotation formats
- no real patient data included
- research/debugging only

## 0.2.0

Added:

- PatchTable abstraction
- CSV/NPY/H5/JSON/PT optional patch coordinate loading
- score/attention loading
- heatmap overlay in viewer
- inspect-patches command
- export-patches command
- render-overlay command
- synthetic demo assets

Changed:

- viewer patch API schema
- README and docs

Security/Compliance:

- no proprietary SDKs
- no proprietary format implementations
- no real slide data included

## 0.1.1

Added:

- release hardening
- env/readers diagnostics
- create-demo
- documentation cleanup

## 0.1.0

Initial MVP:

- inspect
- thumbnail
- doctor
- local viewer
- patch overlay
