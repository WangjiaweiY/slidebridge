from __future__ import annotations

import json

from PIL import Image
from typer.testing import CliRunner

from slidebridge.cli import app


runner = CliRunner()


def test_release_version_output_contains_031():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.3.1" in result.stdout


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


def test_cli_render_view(tmp_path):
    slide = tmp_path / "demo.png"
    coords = tmp_path / "coords.csv"
    view = tmp_path / "view.png"

    assert runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"]).exit_code == 0
    assert runner.invoke(app, ["sample-patches", str(slide), "--out", str(coords), "--count", "20", "--with-scores"]).exit_code == 0
    result = runner.invoke(
        app,
        [
            "render-view",
            str(slide),
            "--patches",
            str(coords),
            "--center-x",
            "256",
            "--center-y",
            "192",
            "--window-width",
            "256",
            "--window-height",
            "192",
            "--out-width",
            "320",
            "--out-height",
            "240",
            "--out",
            str(view),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["out_width"] == 320
    assert payload["out_height"] == 240
    assert view.exists()
    with Image.open(view) as image:
        assert image.size == (320, 240)


def test_cli_render_figure(tmp_path):
    slide = tmp_path / "demo.png"
    heatmap = tmp_path / "heatmap.png"
    figure = tmp_path / "figure.png"

    assert runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"]).exit_code == 0
    Image.new("L", (128, 96), 180).save(heatmap)
    result = runner.invoke(
        app,
        [
            "render-figure",
            str(slide),
            "--raster-heatmap",
            str(heatmap),
            "--center-x",
            "256",
            "--center-y",
            "192",
            "--window-width",
            "256",
            "--window-height",
            "192",
            "--main-width",
            "320",
            "--inset-x",
            "180",
            "--inset-y",
            "120",
            "--inset-width",
            "96",
            "--inset-height",
            "96",
            "--title",
            "Model output overview",
            "--panel-label",
            "A",
            "--scalebar-um",
            "100",
            "--mpp",
            "0.5",
            "--out",
            str(figure),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["inset_bbox"] == [180, 120, 276, 216]
    assert payload["scalebar_drawn"] is True
    assert figure.exists()


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


def test_cli_create_demo_heatmap_matches_slide_aspect(tmp_path):
    slide = tmp_path / "demo.png"
    heatmap = tmp_path / "demo_heatmap.png"

    runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "256"])
    result = runner.invoke(app, ["create-demo-heatmap", "--slide", str(slide), "--out", str(heatmap), "--max-size", "128"])

    assert result.exit_code == 0
    with Image.open(heatmap) as image:
        assert image.size == (128, 64)


def test_cli_inspect_heatmap_raster_json(tmp_path):
    slide = tmp_path / "demo.png"
    heatmap = tmp_path / "heatmap.png"

    runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"])
    Image.new("L", (128, 96), 180).save(heatmap)
    result = runner.invoke(
        app,
        [
            "inspect-heatmap",
            str(heatmap),
            "--slide",
            str(slide),
            "--threshold",
            "0.5",
            "--invert",
            "--colormap",
            "score",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["type"] == "raster"
    assert payload["threshold"] == 0.5
    assert payload["invert"] is True
    assert payload["colormap"] == "score"
    assert payload["slide_width"] == 512


def test_cli_render_overlay_with_raster_heatmap_options(tmp_path):
    slide = tmp_path / "demo.png"
    heatmap = tmp_path / "heatmap.png"
    overlay = tmp_path / "overlay.png"

    runner.invoke(app, ["create-demo", "--out", str(slide), "--width", "512", "--height", "384"])
    Image.new("L", (128, 96), 180).save(heatmap)
    result = runner.invoke(
        app,
        [
            "render-overlay",
            str(slide),
            "--raster-heatmap",
            str(heatmap),
            "--raster-heatmap-threshold",
            "0.25",
            "--raster-heatmap-invert",
            "--raster-heatmap-colormap",
            "score",
            "--out",
            str(overlay),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["raster_heatmap"]["threshold"] == 0.25
    assert payload["raster_heatmap"]["invert"] is True
    assert overlay.exists()
