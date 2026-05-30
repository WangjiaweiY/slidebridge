# Patch Coordinates

SlideBridge patch coordinates use level-0 pixel coordinates.

- `x`, `y`: level-0 pixel location.
- `width`, `height`: level-0 patch size.
- `score` or `attention`: optional model/debug score.
- `label`: optional text label.
- `index`: optional source index.

## CSV

```csv
x,y,width,height,score
10000,20000,512,512,0.82
```

Required columns: `x`, `y`.

Optional columns: `width`, `height`, `score`, `attention`, `label`, `index`.

## NPY

Supported array shapes:

- `(N, 2)`: `x, y`
- `(N, 4)`: `x, y, width, height`
- `(N, >=5)`: `x, y, width, height, score`

If width/height are missing, use `--default-patch-size`.

## H5/HDF5

Recognized coordinate datasets:

- `coords`
- `coordinates`
- `patch_coords`

Recognized score datasets:

- `scores`
- `score`
- `attention`
- `attentions`
- `attention_scores`
- `logits`
- `probs`

SlideBridge also reads useful attributes such as `patch_size`, `patch_level`,
`downsample`, and `mpp` when present. This covers common H5 coordinate layouts
used in research pipelines, but it is not a promise of universal compatibility
with every project.

## JSON

```json
[
  {"x": 100, "y": 200, "width": 256, "height": 256, "score": 0.8}
]
```

or:

```json
{
  "patches": [
    {"x": 100, "y": 200, "width": 256, "height": 256, "score": 0.8}
  ]
}
```

## PT/PTH

`.pt` and `.pth` files are optional and require PyTorch. Supported payloads
include tensors with shape `(N, 2)` or `(N, 4)`, and dictionaries with
coordinate and score keys.
