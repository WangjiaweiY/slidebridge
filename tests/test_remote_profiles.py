from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from slidebridge.cli import app
from slidebridge.remote.profiles import (
    RemoteProfile,
    delete_profile,
    load_profiles,
    profile_config_path,
    resolve_profile_target,
    upsert_profile,
)


runner = CliRunner()


def test_profile_config_path_uses_env(monkeypatch, tmp_path):
    path = tmp_path / "profiles.json"
    monkeypatch.setenv("SLIDEBRIDGE_REMOTE_PROFILES", str(path))

    assert profile_config_path() == path


def test_upsert_and_load_profile(tmp_path):
    path = tmp_path / "profiles.json"
    profile = RemoteProfile(
        name="lab",
        host="server.example.org",
        user="user",
        ssh_port=2222,
        remote_runner="conda run -n slidebridge slidebridge",
        root="/data/slides",
    )

    upsert_profile(profile, path)
    loaded = load_profiles(path)

    assert loaded["lab"].host == "server.example.org"
    assert loaded["lab"].target == "user@server.example.org"
    assert loaded["lab"].resolve_server_path("case.svs") == "/data/slides/case.svs"


def test_resolve_profile_target_absolute_path(tmp_path):
    path = tmp_path / "profiles.json"
    upsert_profile(RemoteProfile(name="lab", host="server.example.org", user="user", root="/data/slides"), path)

    remote, profile = resolve_profile_target("lab:/mnt/slides/case.svs", path=path)

    assert profile is not None
    assert profile.name == "lab"
    assert remote.target == "user@server.example.org"
    assert remote.path == "/mnt/slides/case.svs"


def test_resolve_profile_target_relative_path_uses_root(tmp_path):
    path = tmp_path / "profiles.json"
    upsert_profile(RemoteProfile(name="lab", host="server.example.org", root="/data/slides"), path)

    remote, _ = resolve_profile_target("lab:cohort/case.svs", path=path)

    assert remote.path == "/data/slides/cohort/case.svs"


def test_relative_profile_path_without_root_fails(tmp_path):
    path = tmp_path / "profiles.json"
    upsert_profile(RemoteProfile(name="lab", host="server.example.org"), path)

    with pytest.raises(ValueError, match="has no root path"):
        resolve_profile_target("lab:case.svs", path=path)


def test_delete_profile(tmp_path):
    path = tmp_path / "profiles.json"
    upsert_profile(RemoteProfile(name="lab", host="server.example.org"), path)

    delete_profile("lab", path)

    assert load_profiles(path) == {}


def test_remote_profile_cli_add_list_show_remove(tmp_path):
    path = tmp_path / "profiles.json"
    env = {"SLIDEBRIDGE_REMOTE_PROFILES": str(path)}

    add = runner.invoke(
        app,
        [
            "remote-profile",
            "add",
            "lab",
            "--host",
            "server.example.org",
            "--user",
            "user",
            "--ssh-port",
            "2222",
            "--remote-runner",
            "conda run -n slidebridge slidebridge",
            "--root",
            "/data/slides",
        ],
        env=env,
    )
    assert add.exit_code == 0
    assert "Saved remote profile" in add.stdout

    listed = runner.invoke(app, ["remote-profile", "list", "--json"], env=env)
    assert listed.exit_code == 0
    payload = json.loads(listed.stdout)
    assert payload["profiles"][0]["name"] == "lab"

    shown = runner.invoke(app, ["remote-profile", "show", "lab", "--json"], env=env)
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["root"] == "/data/slides"

    removed = runner.invoke(app, ["remote-profile", "remove", "lab"], env=env)
    assert removed.exit_code == 0
    assert "Removed remote profile" in removed.stdout


def test_remote_view_uses_profile_for_short_command(tmp_path):
    path = tmp_path / "profiles.json"
    env = {"SLIDEBRIDGE_REMOTE_PROFILES": str(path)}
    upsert_profile(
        RemoteProfile(
            name="lab",
            host="server.example.org",
            user="user",
            ssh_port=2222,
            remote_runner="conda run -n slidebridge slidebridge",
            root="/data/slides",
            local_port=7900,
            remote_port=7901,
        ),
        path,
    )

    result = runner.invoke(app, ["remote-view", "lab:case.svs", "--dry-run"], env=env)

    assert result.exit_code == 0
    output = " ".join(result.stdout.split())
    assert "http://127.0.0.1:7900" in output
    assert "-p 2222" in output
    assert "127.0.0.1:7900:127.0.0.1:7901" in output
    assert "conda run -n slidebridge slidebridge view /data/slides/case.svs" in output


def test_remote_ls_uses_profile_root(tmp_path):
    path = tmp_path / "profiles.json"
    env = {"SLIDEBRIDGE_REMOTE_PROFILES": str(path)}
    upsert_profile(RemoteProfile(name="lab", host="server.example.org", root="/data/slides"), path)

    result = runner.invoke(app, ["remote-ls", "lab:", "--dry-run"], env=env)

    assert result.exit_code == 0
    assert "find /data/slides" in result.stdout


def test_remote_inspect_uses_explicit_profile_option(tmp_path):
    path = tmp_path / "profiles.json"
    env = {"SLIDEBRIDGE_REMOTE_PROFILES": str(path)}
    upsert_profile(RemoteProfile(name="lab", host="server.example.org", user="user", root="/data/slides"), path)

    result = runner.invoke(app, ["remote-inspect", "case.svs", "--profile", "lab", "--dry-run"], env=env)

    assert result.exit_code == 0
    assert "user@server.example.org" in result.stdout
    assert "slidebridge inspect /data/slides/case.svs" in result.stdout
