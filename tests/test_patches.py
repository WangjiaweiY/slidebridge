from __future__ import annotations

from slidebridge.overlays.patches import load_patches_csv, validate_patches


def test_load_patches_csv_with_defaults(tmp_path):
    path = tmp_path / "coords.csv"
    path.write_text("x,y,score\n10,20,0.82\n", encoding="utf-8")

    patches = load_patches_csv(path)

    assert patches[0]["x"] == 10
    assert patches[0]["y"] == 20
    assert patches[0]["width"] == 256
    assert patches[0]["height"] == 256
    assert patches[0]["score"] == 0.82


def test_load_patches_csv_width_height_and_score(tmp_path):
    path = tmp_path / "coords.csv"
    path.write_text("x,y,width,height,score\n10.4,20.5,512,128,0.123\n", encoding="utf-8")

    patches = load_patches_csv(path)

    assert patches[0]["x"] == 10
    assert patches[0]["y"] == 20
    assert patches[0]["width"] == 512
    assert patches[0]["height"] == 128
    assert patches[0]["score"] == 0.123


def test_validate_patches_out_of_bounds_does_not_crash():
    patches = [
        {"x": -10, "y": -5, "width": 20, "height": 20, "score": 0.5},
        {"x": 200, "y": 200, "width": 20, "height": 20},
    ]

    validated = validate_patches(patches, slide_width=100, slide_height=80)

    assert len(validated) == 2
    assert validated[0]["x"] == 0
    assert validated[0]["y"] == 0
    assert validated[0]["width"] > 0
    assert validated[1]["x"] == 99
    assert validated[1]["y"] == 79
