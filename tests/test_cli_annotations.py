from __future__ import annotations

import json

from typer.testing import CliRunner

from slidebridge.cli import app


runner = CliRunner()


def test_cli_create_and_inspect_annotations(tmp_path):
    slide = tmp_path / "demo.png"
    annotations = tmp_path / "annotations.geojson"

    assert runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"]).exit_code == 0
    assert runner.invoke(app, ["create-demo-annotations", "--out", str(annotations), "--width", "512", "--height", "384"]).exit_code == 0
    result = runner.invoke(app, ["inspect-annotations", str(annotations), "--slide", str(slide), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] > 0
    assert "Tumor" in payload["labels"]


def test_cli_convert_annotations(tmp_path):
    source = tmp_path / "annotations.geojson"
    target = tmp_path / "annotations.slidebridge.json"

    runner.invoke(app, ["create-demo-annotations", "--out", str(source), "--width", "512", "--height", "384"])
    result = runner.invoke(app, ["convert-annotations", str(source), "--out", str(target)])

    assert result.exit_code == 0
    assert target.exists()


def test_cli_label_patches(tmp_path):
    slide = tmp_path / "demo.png"
    coords = tmp_path / "coords.csv"
    annotations = tmp_path / "annotations.geojson"
    labeled = tmp_path / "coords_labeled.csv"

    runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"])
    runner.invoke(app, ["sample-patches", str(slide), "--out", str(coords), "--count", "20", "--with-scores"])
    runner.invoke(app, ["create-demo-annotations", "--out", str(annotations), "--width", "512", "--height", "384"])
    result = runner.invoke(app, ["label-patches", str(coords), "--annotations", str(annotations), "--out", str(labeled)])

    assert result.exit_code == 0
    assert labeled.exists()
    assert "label_counts" in result.stdout


def test_cli_render_overlay_with_annotations(tmp_path):
    slide = tmp_path / "demo.png"
    annotations = tmp_path / "annotations.geojson"
    overlay = tmp_path / "overlay.png"

    runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"])
    runner.invoke(app, ["create-demo-annotations", "--out", str(annotations), "--width", "512", "--height", "384"])
    result = runner.invoke(app, ["render-overlay", str(slide), "--annotations", str(annotations), "--out", str(overlay)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["annotations_count"] > 0
    assert overlay.exists()
