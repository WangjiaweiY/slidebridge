from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from slidebridge.cli import app


runner = CliRunner()


def test_remote_view_default_localhost_binding():
    result = runner.invoke(app, ["remote-view", "user@example.org:/data/a.svs", "--dry-run"])

    assert result.exit_code == 0
    assert "http://127.0.0.1:7860" in result.stdout
    assert "127.0.0.1:7860:127.0.0.1:7860" in result.stdout
    assert "ServerAliveInterval=30" in result.stdout


def test_remote_view_public_local_bind_warns():
    result = runner.invoke(app, ["remote-view", "user@example.org:/data/a.svs", "--local-host", "0.0.0.0", "--dry-run"])

    assert result.exit_code == 0
    assert "may expose the viewer on your network" in result.stdout


def test_remote_view_public_remote_bind_warns():
    result = runner.invoke(app, ["remote-view", "user@example.org:/data/a.svs", "--remote-host", "0.0.0.0", "--dry-run"])

    assert result.exit_code == 0
    assert "may expose the viewer on your network" in result.stdout


def test_remote_docs_mention_no_automatic_download():
    text = Path("docs/REMOTE_VIEWING.md").read_text(encoding="utf-8")

    assert "does not automatically download" in text
    assert "127.0.0.1" in text
