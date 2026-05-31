from __future__ import annotations

from slidebridge.remote.commands import build_find_command, build_remote_slidebridge_command, quote_remote_arg


def test_quote_remote_arg_handles_spaces():
    assert quote_remote_arg("/data/my slide.svs") == "'/data/my slide.svs'"


def test_quote_remote_arg_preserves_home_expansion():
    assert quote_remote_arg("~/slides/my slide.svs") == "~/'slides/my slide.svs'"


def test_build_remote_slidebridge_command_basic():
    command = build_remote_slidebridge_command("slidebridge", ["inspect", "/data/a.svs"])

    assert command == "slidebridge inspect /data/a.svs"


def test_build_remote_slidebridge_command_with_workdir():
    command = build_remote_slidebridge_command("slidebridge", ["version"], remote_workdir="/opt/project dir")

    assert command == "cd '/opt/project dir' && slidebridge version"


def test_build_remote_slidebridge_command_conda_runner():
    command = build_remote_slidebridge_command(
        "conda run -n slidebridge slidebridge",
        ["view", "/data/a.svs", "--host", "127.0.0.1", "--port", "7860"],
    )

    assert command.startswith("conda run -n slidebridge slidebridge view /data/a.svs")
    assert "--host 127.0.0.1" in command


def test_build_remote_slidebridge_command_quotes_injection_like_path():
    command = build_remote_slidebridge_command("slidebridge", ["inspect", "/data/a; rm -rf /"])

    assert "inspect '/data/a; rm -rf /'" in command


def test_build_find_command_contains_patterns_and_limit():
    command = build_find_command("/data/slides", ["*.svs", "*.tif"], max_depth=3, limit=25)

    assert "find /data/slides -maxdepth 3" in command
    assert "-name '*.svs'" in command
    assert "head -n 25" in command
