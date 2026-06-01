from __future__ import annotations

import json

from PIL import Image
from typer.testing import CliRunner

from slidebridge.cli import app


runner = CliRunner()


def test_release_version_output_contains_024():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.2.4" in result.stdout


def test_cli_render_overlay(tmp_path):
    slide = tmp_path / "demo.png"
    coords = tmp_path / "coords.csv"
    overlay = tmp_path / "overlay.png"

    assert runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"]).exit_code == 0
    assert runner.invoke(app, ["sample-patches", str(slide), "--out", str(coords), "--count", "20", "--with-scores"]).exit_code == 0
    result = runner.invoke(app, ["render-overlay", str(slide), "--patches", str(coords), "--out", str(overlay), "--max-size", "256"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["patches_count"] == 20
    assert overlay.exists()
    with Image.open(overlay) as image:
        assert max(image.size) <= 256


def test_cli_render_overlay_without_scores(tmp_path):
    slide = tmp_path / "demo.png"
    coords = tmp_path / "coords.csv"
    overlay = tmp_path / "overlay.png"

    runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"])
    runner.invoke(app, ["sample-patches", str(slide), "--out", str(coords), "--count", "10", "--no-scores"])
    result = runner.invoke(app, ["render-overlay", str(slide), "--patches", str(coords), "--out", str(overlay)])

    assert result.exit_code == 0
    assert overlay.exists()


def test_cli_render_overlay_with_raster_heatmap(tmp_path):
    slide = tmp_path / "demo.png"
    heatmap = tmp_path / "heatmap.png"
    overlay = tmp_path / "raster_overlay.png"

    runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"])
    Image.new("L", (64, 48), 180).save(heatmap)
    result = runner.invoke(app, ["render-overlay", str(slide), "--heatmap", str(heatmap), "--out", str(overlay)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["raster_heatmap"]["available"] is True
    assert overlay.exists()


def test_cli_create_demo_heatmap(tmp_path):
    heatmap = tmp_path / "demo_heatmap.jpg"

    result = runner.invoke(app, ["create-demo-heatmap", "--out", str(heatmap), "--width", "128", "--height", "96"])

    assert result.exit_code == 0
    assert heatmap.exists()
    with Image.open(heatmap) as image:
        assert image.size == (128, 96)
