from __future__ import annotations

from typer.testing import CliRunner

from slidebridge.cli import app
from slidebridge.remote.diagnostics import RemoteCommandResult


runner = CliRunner()


def test_remote_view_dry_run_prints_tunnel_and_remote_command():
    result = runner.invoke(
        app,
        [
            "remote-view",
            "user@example.org:/data/slides/demo.svs",
            "--remote-runner",
            "conda run -n slidebridge slidebridge",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Local URL" in result.stdout
    assert "ExitOnForwardFailure=yes" in result.stdout
    assert "-L 127.0.0.1:7860:127.0.0.1:7860 user@example.org" in result.stdout
    assert "conda run -n slidebridge slidebridge view /data/slides/demo.svs" in result.stdout
    assert "--no-open-browser" in result.stdout
    assert "--viewer-context remote" in result.stdout
    assert "--viewer-remote-user user" in result.stdout
    assert "--viewer-remote-host example.org" in result.stdout


def test_remote_inspect_dry_run_prints_command():
    result = runner.invoke(
        app,
        [
            "remote-inspect",
            "user@example.org:/data/slides/demo.svs",
            "--remote-runner",
            "conda run -n slidebridge slidebridge",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "slidebridge inspect /data/slides/demo.svs" in result.stdout


def test_remote_ls_dry_run_prints_find():
    result = runner.invoke(app, ["remote-ls", "user@example.org:/data/slides", "--dry-run"])

    assert result.exit_code == 0
    assert "find /data/slides" in result.stdout
    assert "user@example.org" in result.stdout


def test_remote_check_dry_run_prints_diagnostics_commands():
    result = runner.invoke(
        app,
        [
            "remote-check",
            "user@example.org",
            "--remote-runner",
            "conda run -n slidebridge slidebridge",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "slidebridge version" in result.stdout
    assert "slidebridge readers" in result.stdout


def test_remote_view_dry_run_with_overlays():
    result = runner.invoke(
        app,
        [
            "remote-view",
            "user@example.org:/data/slides/demo.svs",
            "--patches",
            "/data/features/coords.h5",
            "--annotations",
            "/data/annotations/case.geojson",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "--patches /data/features/coords.h5" in result.stdout
    assert "--annotations /data/annotations/case.geojson" in result.stdout


def test_remote_view_dry_run_directory_mode():
    result = runner.invoke(
        app,
        [
            "remote-view",
            "user@example.org:/data/slides",
            "--recursive",
            "--max-slides",
            "25",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "slidebridge view /data/slides" in result.stdout
    assert "--recursive" in result.stdout
    assert "--max-slides 25" in result.stdout


def test_remote_inspect_mocked_execution(monkeypatch):
    def fake_require_ssh_available() -> None:
        return None

    def fake_run_ssh_command(command, timeout=None):
        return RemoteCommandResult(command=command, returncode=0, stdout="inspect-ok\n", stderr="")

    monkeypatch.setattr("slidebridge.cli.require_ssh_available", fake_require_ssh_available)
    monkeypatch.setattr("slidebridge.cli.run_ssh_command", fake_run_ssh_command)

    result = runner.invoke(app, ["remote-inspect", "user@example.org:/data/slides/demo.svs"])

    assert result.exit_code == 0
    assert "inspect-ok" in result.stdout


def test_remote_view_reports_occupied_remote_port(monkeypatch):
    def fake_require_ssh_available() -> None:
        return None

    def fake_run_ssh_command(command, timeout=None):
        assert "ss -ltn" in command[-1]
        return RemoteCommandResult(command=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("slidebridge.cli.require_ssh_available", fake_require_ssh_available)
    monkeypatch.setattr("slidebridge.cli.is_local_port_available", lambda host, port: True)
    monkeypatch.setattr("slidebridge.cli.run_ssh_command", fake_run_ssh_command)

    result = runner.invoke(app, ["remote-view", "user@example.org:/data/slides/demo.svs", "--no-open-browser"])

    assert result.exit_code == 1
    assert "Remote port 7860" in result.stdout
    assert "already in use" in result.stdout


def test_remote_view_remote_port_preflight_failure_stops_before_start(monkeypatch):
    def fake_require_ssh_available() -> None:
        return None

    def fake_run_ssh_command(command, timeout=None):
        return RemoteCommandResult(command=command, returncode=255, stdout="", stderr="ssh failed")

    def fail_if_started(command):
        raise AssertionError("remote-view should not start SSH tunnel when preflight fails")

    monkeypatch.setattr("slidebridge.cli.require_ssh_available", fake_require_ssh_available)
    monkeypatch.setattr("slidebridge.cli.is_local_port_available", lambda host, port: True)
    monkeypatch.setattr("slidebridge.cli.run_ssh_command", fake_run_ssh_command)
    monkeypatch.setattr("slidebridge.cli.subprocess.Popen", fail_if_started)

    result = runner.invoke(app, ["remote-view", "user@example.org:/data/slides/demo.svs", "--no-open-browser"])

    assert result.exit_code == 1
    assert "Remote port preflight check failed" in result.stdout


def test_remote_view_keyboard_interrupt_cleans_remote_viewer(monkeypatch):
    calls = []

    def fake_require_ssh_available() -> None:
        return None

    def fake_run_ssh_command(command, timeout=None):
        calls.append(command[-1])
        if "ss -ltn" in command[-1]:
            return RemoteCommandResult(command=command, returncode=1, stdout="", stderr="")
        if "slidebridge view" in command[-1] and "kill" in command[-1]:
            return RemoteCommandResult(command=command, returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected remote command: {command[-1]}")

    class FakeProcess:
        def __init__(self, command):
            self.command = command
            self.terminated = False

        def wait(self, timeout=None):
            if timeout is None:
                raise KeyboardInterrupt()
            return 0

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.terminated = True

        def poll(self):
            return None

    monkeypatch.setattr("slidebridge.cli.require_ssh_available", fake_require_ssh_available)
    monkeypatch.setattr("slidebridge.cli.is_local_port_available", lambda host, port: True)
    monkeypatch.setattr("slidebridge.cli.wait_for_http", lambda url, timeout=30.0: True)
    monkeypatch.setattr("slidebridge.cli.webbrowser.open", lambda url: None)
    monkeypatch.setattr("slidebridge.cli.run_ssh_command", fake_run_ssh_command)
    monkeypatch.setattr("slidebridge.cli.subprocess.Popen", FakeProcess)

    result = runner.invoke(app, ["remote-view", "user@example.org:/data/slides/demo.svs"])

    assert result.exit_code == 0
    assert "Stopping SSH tunnel" in result.stdout
    assert "Stopping remote SlideBridge viewer on port 7860" in result.stdout
    assert "Remote viewer stopped" in result.stdout
    assert any("kill $pids" in command for command in calls)


def test_remote_view_cleanup_success_uses_port_state_not_kill_returncode(monkeypatch):
    calls = []

    def fake_require_ssh_available() -> None:
        return None

    def fake_run_ssh_command(command, timeout=None):
        calls.append(command[-1])
        if "ss -ltn" in command[-1]:
            return RemoteCommandResult(command=command, returncode=1, stdout="", stderr="")
        if "slidebridge view" in command[-1] and "kill" in command[-1]:
            return RemoteCommandResult(command=command, returncode=255, stdout="", stderr="terminated")
        raise AssertionError(f"unexpected remote command: {command[-1]}")

    class FakeProcess:
        def __init__(self, command):
            self.command = command

        def wait(self, timeout=None):
            if timeout is None:
                raise KeyboardInterrupt()
            return 0

        def terminate(self):
            return None

        def kill(self):
            return None

        def poll(self):
            return None

    monkeypatch.setattr("slidebridge.cli.require_ssh_available", fake_require_ssh_available)
    monkeypatch.setattr("slidebridge.cli.is_local_port_available", lambda host, port: True)
    monkeypatch.setattr("slidebridge.cli.wait_for_http", lambda url, timeout=30.0: True)
    monkeypatch.setattr("slidebridge.cli.webbrowser.open", lambda url: None)
    monkeypatch.setattr("slidebridge.cli.run_ssh_command", fake_run_ssh_command)
    monkeypatch.setattr("slidebridge.cli.subprocess.Popen", FakeProcess)

    result = runner.invoke(app, ["remote-view", "user@example.org:/data/slides/demo.svs"])

    assert result.exit_code == 0
    assert "Remote viewer stopped" in result.stdout
    assert "Remote cleanup could not confirm" not in result.stdout
