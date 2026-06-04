from __future__ import annotations

from importlib import resources

from fastapi.testclient import TestClient

from slidebridge.app.server import create_launcher_app
from slidebridge.remote.diagnostics import RemoteCommandResult


def test_launcher_index_and_static_assets_are_available(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))
    client = TestClient(create_launcher_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "SlideBridge 启动器" in response.text
    assert "slidebridge-app-config" in response.text
    assert "/static/app.css" in response.text
    assert "/static/app.js" in response.text
    assert "profile-select" in response.text
    assert "language-select" in response.text

    css = client.get("/static/app.css")
    js = client.get("/static/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "远端文件浏览器" in response.text
    assert 'remoteFileBrowser: "Remote file browser"' in js.text
    assert "renderProfiles" in js.text
    assert "applySelectedProfile" in js.text
    assert "changeLanguage" in js.text


def test_launcher_assets_are_packaged():
    app_root = resources.files("slidebridge.app")
    template = app_root.joinpath("templates", "app.html")
    css = app_root.joinpath("static", "app.css")
    js = app_root.joinpath("static", "app.js")

    assert template.is_file()
    assert css.is_file()
    assert js.is_file()
    assert "slidebridge-app-config" in template.read_text(encoding="utf-8")
    assert "远端文件浏览器" in template.read_text(encoding="utf-8")
    assert "language-select" in template.read_text(encoding="utf-8")
    assert "fetchJson" in js.read_text(encoding="utf-8")
    assert "Viewer Launcher" in js.read_text(encoding="utf-8")


def test_session_command_builds_remote_view_command(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))
    client = TestClient(create_launcher_app())

    response = client.post(
        "/api/session/command",
        json={
            "host": "server.example.org",
            "user": "user",
            "ssh_port": "2222",
            "remote_runner": "conda run -n slidebridge slidebridge",
            "remote_path": "/data/slides/case.svs",
            "local_port": "7900",
            "remote_port": "7901",
            "patches": "/data/features/coords.h5",
            "annotations": "/data/annotations/case.geojson",
            "annotation_format": "qupath-geojson",
            "raster_heatmap_layers": [{"name": "low", "path": "/data/heatmaps/low.png"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    command = payload["command"]
    assert payload["mode"] == "remote"
    assert payload["status"] == "prepared"
    assert payload["viewer_url"] == "http://127.0.0.1:7900"
    assert "remote-view user@server.example.org:/data/slides/case.svs" in command
    assert "--ssh-port 2222" in command
    assert "--remote-runner" in command
    assert "conda run -n slidebridge slidebridge" in command
    assert "--local-port 7900" in command
    assert "--remote-port 7901" in command
    assert "--raster-heatmap-layer low=/data/heatmaps/low.png" in command
    assert "--patches /data/features/coords.h5" in command
    assert "--annotations /data/annotations/case.geojson" in command
    assert "--annotation-format qupath-geojson" in command
    assert "--no-open-browser" in command


def test_remote_list_api_parses_entries(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))

    def fake_run_ssh_command(command, timeout=None):
        assert "find /data/slides -mindepth 1 -maxdepth 1" in command[-1]
        return RemoteCommandResult(
            command=command,
            returncode=0,
            stdout=(
                "d\t/data/slides\t4096\t2026-06-01 10:00\n"
                "f\t/data/slides/case.svs\t123\t2026-06-01 10:01\n"
                "f\t/data/slides/heatmap.png\t456\t2026-06-01 10:02\n"
                "f\t/data/slides/anno.geojson\t789\t2026-06-01 10:03\n"
            ),
            stderr="",
        )

    monkeypatch.setattr("slidebridge.app.remote.run_ssh_command", fake_run_ssh_command)
    client = TestClient(create_launcher_app())

    response = client.post("/api/remote/list", json={"host": "server.example.org", "remote_dir": "/data/slides"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["entries"]) == 4
    assert payload["entries"][1]["is_slide"] is True
    assert payload["entries"][2]["is_heatmap"] is True
    assert payload["entries"][3]["is_annotation"] is True


def test_remote_test_api_reports_command_result(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))
    monkeypatch.setattr("slidebridge.app.remote.require_ssh_available", lambda: None)

    def fake_run_ssh_command(command, timeout=None):
        return RemoteCommandResult(command=command, returncode=0, stdout="SlideBridge Core version: 0.3.0\n", stderr="")

    monkeypatch.setattr("slidebridge.app.remote.run_ssh_command", fake_run_ssh_command)
    client = TestClient(create_launcher_app())

    response = client.post("/api/remote/test", json={"host": "server.example.org", "remote_runner": "slidebridge"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "0.3.0" in payload["stdout"]


def test_session_launch_list_and_stop(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))

    class FakeProcess:
        def __init__(self, command):
            self.command = command
            self.running = True

        def poll(self):
            return None if self.running else 0

        def terminate(self):
            self.running = False

        def wait(self, timeout=None):
            self.running = False
            return 0

        def kill(self):
            self.running = False

    monkeypatch.setattr("slidebridge.app.sessions.subprocess.Popen", FakeProcess)
    client = TestClient(create_launcher_app())

    launch = client.post("/api/session/launch", json={"host": "server.example.org", "remote_path": "/data/slides/case.svs"})

    assert launch.status_code == 200
    session_id = launch.json()["id"]
    assert launch.json()["status"] == "running"

    listed = client.get("/api/session/list")
    assert listed.status_code == 200
    assert listed.json()["sessions"][0]["id"] == session_id

    stopped = client.post(f"/api/session/{session_id}/stop", json={})
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"


def test_invalid_remote_path_returns_400(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))
    client = TestClient(create_launcher_app())

    response = client.post("/api/session/command", json={"host": "server.example.org", "remote_path": "relative.svs"})

    assert response.status_code == 400
    assert "Remote path must start" in response.json()["detail"]
