# Windows Setup

## Conda Environment

```powershell
conda create -n slidebridge python=3.11 -y
conda activate slidebridge
pip install tiffslide openslide-python openslide-bin pillow numpy pandas `
  fastapi uvicorn typer rich jinja2 pytest h5py
pip install -e .
```

`openslide-bin` can provide the Windows DLLs required by `openslide-python`.

## Diagnostics

```powershell
slidebridge env
slidebridge readers
```

## Common Errors

### OpenSlide DLL not found

Install `openslide-bin` in the active environment:

```powershell
pip install openslide-bin
```

Then run:

```powershell
slidebridge readers
```

### No available reader

Run:

```powershell
slidebridge readers
slidebridge env
```

Check that the file exists and that at least one reader is available.

### Viewer asset not loading

The viewer first uses the OpenSeadragon asset bundled with SlideBridge. If that
local asset cannot load, it falls back to the CDN. Metadata, thumbnail export,
patch sampling, and doctor reports do not require the browser viewer asset.
