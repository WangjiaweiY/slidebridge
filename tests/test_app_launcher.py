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
    assert "remote-runtime" in response.text
    assert "open-viewer" not in response.text
    assert "远端环境" in response.text
    assert "session-list" not in response.text
    assert "Viewer 会话" not in response.text
    assert "conda-env-path" in response.text
    assert "browse-conda-env-path" in response.text
    assert "remote-browser-modal" in response.text
    assert "remote-path" not in response.text
    assert "remote-dir" not in response.text
    assert "heatmap-layers" not in response.text
    assert "远端文件浏览器" not in response.text

    css = client.get("/static/app.css")
    js = client.get("/static/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "renderProfiles" in js.text
    assert "applySelectedProfile" in js.text
    assert "changeLanguage" in js.text
    assert "conda_env_path" in js.text
    assert "loadRemoteBrowserDirectory" in js.text
    assert "remoteDirectoryBrowser" in js.text
    assert "remoteWorkdirHint" in js.text
    assert "modal-backdrop" in css.text
    assert 'remoteRuntime: "Run with"' in js.text
    assert "pickCondaCommand" not in js.text


def test_launcher_assets_are_packaged():
    app_root = resources.files("slidebridge.app")
    template = app_root.joinpath("templates", "app.html")
    css = app_root.joinpath("static", "app.css")
    js = app_root.joinpath("static", "app.js")

    assert template.is_file()
    assert css.is_file()
    assert js.is_file()
    assert "slidebridge-app-config" in template.read_text(encoding="utf-8")
    assert "浏览目录" in template.read_text(encoding="utf-8")
    assert "language-select" in template.read_text(encoding="utf-8")
    assert "remote-runtime" in template.read_text(encoding="utf-8")
    assert "browse-conda-env-path" in template.read_text(encoding="utf-8")
    assert "remote-browser-modal" in template.read_text(encoding="utf-8")
    assert "open-viewer" not in template.read_text(encoding="utf-8")
    assert "remote-path" not in template.read_text(encoding="utf-8")
    assert "fetchJson" in js.read_text(encoding="utf-8")
    assert "loadRemoteBrowserDirectory" in js.read_text(encoding="utf-8")
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
            "conda_env_path": "/home/user/miniconda3/envs/slidebridge",
            "remote_home": "/home/user",
            "local_port": "7900",
            "remote_port": "7901",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    command = payload["command"]
    assert payload["mode"] == "remote"
    assert payload["status"] == "prepared"
    assert payload["viewer_url"] == "http://127.0.0.1:7900"
    assert "remote-view user@server.example.org:/home/user" in command
    assert "--ssh-port 2222" in command
    assert "--remote-runner" in command
    assert "/home/user/miniconda3/envs/slidebridge/bin/python" in command
    assert "-m slidebridge.cli" in command
    assert "--local-port 7900" in command
    assert "--remote-port 7901" in command
    assert "--raster-heatmap-layer" not in command
    assert "--patches" not in command
    assert "--annotations" not in command
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
        assert "slidebridge-ssh-ok" in command[-1]
        return RemoteCommandResult(command=command, returncode=0, stdout="slidebridge-ssh-ok\n/home/user\n", stderr="")

    monkeypatch.setattr("slidebridge.app.remote.run_ssh_command", fake_run_ssh_command)
    client = TestClient(create_launcher_app())

    response = client.post("/api/remote/test", json={"host": "server.example.org", "remote_runner": "slidebridge"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "slidebridge-ssh-ok" in payload["stdout"]
    assert payload["remote_home"] == "/home/user"


def test_remote_runtime_test_api_reports_slidebridge_result(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))
    monkeypatch.setattr("slidebridge.app.remote.require_ssh_available", lambda: None)

    def fake_run_ssh_command(command, timeout=None):
        assert "/home/user/miniconda3/envs/slidebridge/bin/python" in command[-1]
        assert "-m slidebridge.cli version" in command[-1]
        return RemoteCommandResult(command=command, returncode=0, stdout="SlideBridge Core version: 0.3.1\n", stderr="")

    monkeypatch.setattr("slidebridge.app.remote.run_ssh_command", fake_run_ssh_command)
    client = TestClient(create_launcher_app())

    response = client.post(
        "/api/remote/runtime-test",
        json={"host": "server.example.org", "conda_env_path": "/home/user/miniconda3/envs/slidebridge"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "0.3.1" in payload["stdout"]


def test_session_launch_list_and_stop(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))

    class FakeProcess:
        instances = []

        def __init__(self, command):
            self.command = command
            self.running = True
            self.terminated = False
            self.killed = False
            FakeProcess.instances.append(self)

        def poll(self):
            return None if self.running else 0

        def terminate(self):
            self.terminated = True
            self.running = False

        def wait(self, timeout=None):
            self.running = False
            return 0

        def kill(self):
            self.killed = True
            self.running = False

    monkeypatch.setattr("slidebridge.app.sessions.subprocess.Popen", FakeProcess)
    monkeypatch.setattr("slidebridge.app.server.wait_for_http", lambda url, timeout=30.0: True)
    client = TestClient(create_launcher_app())

    first_launch = client.post(
        "/api/session/launch",
        json={"host": "server.example.org", "remote_home": "/home/user/first", "local_port": "7900"},
    )

    assert first_launch.status_code == 200
    first_session_id = first_launch.json()["id"]
    assert first_launch.json()["status"] == "running"
    assert first_launch.json()["ready"] is True

    second_launch = client.post(
        "/api/session/launch",
        json={"host": "server.example.org", "remote_home": "/home/user/second", "local_port": "7901"},
    )

    assert second_launch.status_code == 200
    session_id = second_launch.json()["id"]
    assert session_id != first_session_id
    assert second_launch.json()["status"] == "running"
    assert second_launch.json()["ready"] is True
    assert FakeProcess.instances[0].terminated is True

    listed = client.get("/api/session/list")
    assert listed.status_code == 200
    assert len(listed.json()["sessions"]) == 1
    assert listed.json()["sessions"][0]["id"] == session_id

    old_stop = client.post(f"/api/session/{first_session_id}/stop", json={})
    assert old_stop.status_code == 404

    stopped = client.post(f"/api/session/{session_id}/stop", json={})
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"


def test_invalid_remote_path_returns_400(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(tmp_path / "profiles.json"))
    client = TestClient(create_launcher_app())

    response = client.post("/api/session/command", json={"host": "server.example.org", "remote_path": "relative.svs"})

    assert response.status_code == 400
    assert "Remote path must start" in response.json()["detail"]
