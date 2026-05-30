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
    assert "ssh -L 127.0.0.1:7860:127.0.0.1:7860 user@example.org" in result.stdout
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
