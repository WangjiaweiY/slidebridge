# Contributing

Thanks for considering a contribution to SlideBridge Core. This project is a
research and algorithm debugging toolkit, not clinical software.

## Development Setup

```powershell
git clone https://github.com/WangjiaweiY/slidebridge.git
cd slidebridge
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e .[dev]
```

On Windows, `openslide-bin` can help provide the OpenSlide runtime used by
`openslide-python`. The synthetic demo workflows do not require a real WSI.

## Run Tests

```powershell
pytest -q
```

## Run The Quick Demo

```powershell
slidebridge create-demo --out outputs\demo_slide.png
slidebridge sample-patches outputs\demo_slide.png --out outputs\demo_coords.csv `
  --count 100 --with-scores
slidebridge render-overlay outputs\demo_slide.png --patches outputs\demo_coords.csv `
  --out outputs\demo_overlay.png
slidebridge inspect outputs\demo_slide.png
```

## Coding Style

- Keep changes focused and small.
- Prefer `pathlib.Path` for filesystem paths.
- Keep optional dependencies optional and fail with clear messages.
- Add tests for new CLI behavior and data formats.
- Keep docs updated for user-facing behavior.

## Data And Compliance Rules

- Do not include patient-identifiable data in issues, pull requests, tests, or
  example assets.
- Do not attach proprietary data, private documentation, SDKs, runtime
  libraries, headers, or vendor binaries.
- Do not add proprietary format implementations to the public core.
- Keep examples based on synthetic data or small generated images.
- SlideBridge Core is for research and debugging only, not clinical diagnosis.

## Proposing A New Public Reader

Public readers should wrap public, redistributable libraries and use the
existing reader registry. A proposal should explain the public dependency,
license, supported open data model, expected maintenance burden, and test plan.
Reader code that depends on private agreements or non-redistributable assets
belongs in a separately licensed private package, not in SlideBridge Core.
