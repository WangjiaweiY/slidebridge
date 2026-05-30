# Changelog

## 0.2.2

Added:

- Remote WSI viewing over SSH tunnel
- remote-view command
- remote-check command
- remote-ls command
- remote-inspect command
- remote command builder utilities
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
