from __future__ import annotations

import pytest

from slidebridge.remote.spec import is_remote_spec, parse_remote_path


def test_parse_remote_user_host_absolute_path():
    remote = parse_remote_path("user@server:/data/a.svs")

    assert remote.user == "user"
    assert remote.host == "server"
    assert remote.path == "/data/a.svs"
    assert remote.target == "user@server"


def test_parse_remote_host_absolute_path():
    remote = parse_remote_path("server:/data/a.svs")

    assert remote.user is None
    assert remote.host == "server"
    assert remote.path == "/data/a.svs"


def test_parse_remote_home_path():
    remote = parse_remote_path("server:~/slides/a.svs")

    assert remote.host == "server"
    assert remote.path == "~/slides/a.svs"


def test_windows_paths_are_not_remote_specs():
    assert is_remote_spec(r"C:\Users\a.svs") is False
    assert is_remote_spec(r"D:\slides\a.svs") is False


def test_invalid_remote_path_raises_clear_error():
    with pytest.raises(ValueError, match="Remote path must start"):
        parse_remote_path("server:relative/path.svs")


def test_missing_remote_separator_raises_clear_error():
    with pytest.raises(ValueError, match="Remote path must use"):
        parse_remote_path("server")
