from __future__ import annotations

from slidebridge.remote.ssh import build_ssh_base_command


def test_build_ssh_base_command_host_only():
    assert build_ssh_base_command("server") == ["ssh", "server"]


def test_build_ssh_base_command_user_host():
    assert build_ssh_base_command("server", user="user") == ["ssh", "user@server"]


def test_build_ssh_base_command_port():
    assert build_ssh_base_command("server", port=2222) == ["ssh", "-p", "2222", "server"]


def test_build_ssh_base_command_identity_file():
    command = build_ssh_base_command("server", identity_file=r"C:\keys\id_ed25519")

    assert command == ["ssh", "-i", r"C:\keys\id_ed25519", "server"]


def test_build_ssh_base_command_options_are_split():
    command = build_ssh_base_command("server", ssh_options=["-J bastion", "-o ServerAliveInterval=30"])

    assert command == ["ssh", "-J", "bastion", "-o", "ServerAliveInterval=30", "server"]


def test_build_ssh_base_command_returns_list():
    command = build_ssh_base_command("server")

    assert isinstance(command, list)
    assert all(isinstance(part, str) for part in command)
