# GitHub Repository Settings TODO

## About

Repository description:

```text
Lightweight WSI inspection, patch debugging, and model-output visualization
toolkit for computational pathology.
```

Website:

```text
Leave blank for now, or add GitHub Pages/docs later.
```

## Topics

- computational-pathology
- digital-pathology
- whole-slide-image
- wsi
- pathology-ai
- histopathology
- medical-imaging
- image-processing
- openslide
- tiffslide
- python
- fastapi
- qupath
- pathology
- ai

## Release

- Create a GitHub Release from the existing tag `v0.2.0`.
- Title: `SlideBridge Core v0.2.0`
- Body: use `release_notes/v0.2.0.md`.
- Attach `dist/*.whl` and `dist/*.tar.gz` if desired.
- Do not publish to PyPI yet.
- Do not move or recreate the existing tag.

Prepared command if GitHub CLI is already authenticated:

```powershell
gh release create v0.2.0 dist/*.whl dist/*.tar.gz `
  --title "SlideBridge Core v0.2.0" `
  --notes-file release_notes/v0.2.0.md
```
