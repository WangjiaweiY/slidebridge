from __future__ import annotations

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from slidebridge.cli import app


runner = CliRunner()


def test_root_version_option():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "SlideBridge Core 0.3.0" in result.stdout


def test_version_command():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "SlideBridge Core version: 0.3.0" in result.stdout
    assert "Python version:" in result.stdout


def test_app_command_starts_launcher_without_browser(monkeypatch):
    captured = {}

    def fake_run(web_app, host, port, log_level):
        captured["title"] = web_app.title
        captured["host"] = host
        captured["port"] = port
        captured["log_level"] = log_level

    monkeypatch.setattr("slidebridge.cli.uvicorn.run", fake_run)
    monkeypatch.setattr("slidebridge.cli.webbrowser.open", lambda url: captured.setdefault("opened", url))

    result = runner.invoke(app, ["app", "--port", "7855", "--no-open-browser"])

    assert result.exit_code == 0
    assert "Starting SlideBridge App: http://127.0.0.1:7855" in result.stdout
    assert captured["title"] == "SlideBridge App"
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 7855
    assert captured["log_level"] == "info"
    assert "opened" not in captured


def test_env_command_does_not_crash():
    result = runner.invoke(app, ["env"])

    assert result.exit_code == 0
    assert "Package Diagnostics" in result.stdout


def test_readers_command_does_not_crash():
    result = runner.invoke(app, ["readers"])

    assert result.exit_code == 0
    assert "Registered Readers" in result.stdout
    assert "tiffslide" in result.stdout
    assert "image" in result.stdout


def test_create_demo_and_inspect(tmp_path):
    demo_path = tmp_path / "demo_slide.png"

    create_result = runner.invoke(
        app,
        [
            "create-demo",
            "--out",
            str(demo_path),
            "--width",
            "512",
            "--height",
            "384",
            "--seed",
            "7",
        ],
    )
    assert create_result.exit_code == 0
    assert demo_path.exists()

    inspect_result = runner.invoke(app, ["inspect", str(demo_path), "--reader", "image", "--json"])
    assert inspect_result.exit_code == 0
    payload = json.loads(inspect_result.stdout)
    assert payload["reader"] == "image"
    assert payload["width"] == 512
    assert payload["height"] == 384


def test_view_accepts_tile_performance_options(tmp_path, monkeypatch):
    demo_path = tmp_path / "demo_slide.png"
    runner.invoke(app, ["create-demo", "--out", str(demo_path), "--width", "256", "--height", "256"])

    captured = {}

    def fake_run(viewer_app, host, port):
        captured["host"] = host
        captured["port"] = port
        client = TestClient(viewer_app)
        stats = client.get("/api/cache-stats").json()
        captured["stats"] = stats

    monkeypatch.setattr("slidebridge.cli.uvicorn.run", fake_run)
    result = runner.invoke(
        app,
        [
            "view",
            str(demo_path),
            "--reader",
            "image",
            "--tile-cache-size",
            "128",
            "--tile-cache-mb",
            "64",
            "--tile-workers",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 7860
    assert captured["stats"]["max_entries"] == 128
    assert captured["stats"]["max_mb"] == 64
    assert captured["stats"]["tile_workers"] == 2
