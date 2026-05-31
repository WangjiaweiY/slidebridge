# Label Patches

`slidebridge label-patches` assigns annotation-derived labels to patch
coordinates for debugging and weak-label inspection.

```powershell
slidebridge label-patches outputs\coords.csv --annotations outputs\annotations.geojson --out outputs\coords_labeled.csv
```

## Methods

`center` is the default. A patch receives an annotation label when the patch
center point falls inside the annotation geometry.

`bbox` is approximate. It labels a patch when the patch rectangle intersects an
annotation bounding box. It does not compute exact polygon overlap.

## Single-Label Policy

In single-label mode, if multiple annotations match one patch, SlideBridge uses
the smallest annotation area first, then the original annotation order.

## Multi-Label Mode

In multi-label mode, all matched labels are joined with semicolons, for example:

```text
Tumor;Necrosis
```

## Output Columns

CSV output includes:

- `index`
- `x`
- `y`
- `width`
- `height`
- `score` when included
- `label`
- `matched_annotation_id`
- `matched_annotation_type`
- `matched_annotation_label`

## Limitations

This command is a debugging helper. It does not create clinical labels and does
not replace expert review or project-specific labeling policy.
