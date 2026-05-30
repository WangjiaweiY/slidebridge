from __future__ import annotations

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from slidebridge.cli import app
from slidebridge.server.app import create_app
from slidebridge.utils.demo import create_demo_slide


runner = CliRunner()


def test_sample_patches_format_npy(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=3)
    out = tmp_path / "coords.npy"

    result = runner.invoke(app, ["sample-patches", str(slide), "--out", str(out), "--format", "npy", "--count", "5"])

    assert result.exit_code == 0
    assert out.exists()


def test_sample_patches_format_h5(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=4)
    out = tmp_path / "coords.h5"

    result = runner.invoke(app, ["sample-patches", str(slide), "--out", str(out), "--format", "h5", "--count", "5"])

    assert result.exit_code == 0
    assert out.exists()


def test_inspect_patches_command(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=5)
    coords = tmp_path / "coords.csv"
    runner.invoke(app, ["sample-patches", str(slide), "--out", str(coords), "--format", "csv", "--count", "5"])

    result = runner.invoke(app, ["inspect-patches", str(coords), "--slide", str(slide)])

    assert result.exit_code == 0
    assert "PatchTable Inspect" in result.stdout
    assert "count" in result.stdout


def test_export_patches_command(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=6)
    coords = tmp_path / "coords.csv"
    out_dir = tmp_path / "patches"
    runner.invoke(app, ["sample-patches", str(slide), "--out", str(coords), "--format", "csv", "--count", "5"])

    result = runner.invoke(app, ["export-patches", str(slide), "--patches", str(coords), "--out", str(out_dir), "--limit", "2"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["exported"] == 2
    assert (out_dir / "manifest.csv").exists()


def test_view_app_patches_new_json_schema(tmp_path):
    slide = create_demo_slide(tmp_path / "demo.png", width=512, height=384, seed=7)
    coords = tmp_path / "coords.csv"
    coords.write_text("x,y,width,height,score\n10,20,64,64,0.5\n", encoding="utf-8")
    viewer = create_app(slide, patches_path=coords, reader="image")
    client = TestClient(viewer)

    response = client.get("/api/patches")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["returned"] == 1
    assert payload["has_scores"] is True
    assert payload["patches"][0]["score"] == 0.5
