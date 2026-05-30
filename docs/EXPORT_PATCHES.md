# Export Patches

Export patch images from a slide and a coordinate file:

```powershell
slidebridge export-patches C:\path\to\your\slide.svs --patches outputs\coords.csv --out outputs\patches --limit 50
```

## Output Naming

Patch images are named:

```text
patch_000000_x10000_y20000_w512_h512.jpg
```

Use `--prefix` to change the filename prefix.

## Manifest

`manifest.csv` contains:

```text
index,x,y,width,height,score,label,image_path
```

## Boundary Behavior

- Fully outside patches are skipped.
- Partially outside patches are clipped to slide bounds.
- Individual patch failures are counted and do not stop the whole export.

## Formats

```powershell
slidebridge export-patches C:\path\to\your\slide.svs --patches outputs\coords.csv --out outputs\patches --format jpg
slidebridge export-patches C:\path\to\your\slide.svs --patches outputs\coords.csv --out outputs\patches_png --format png
```
