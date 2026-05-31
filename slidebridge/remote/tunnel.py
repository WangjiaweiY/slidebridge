from __future__ import annotations

import socket
import time
from urllib.error import URLError
from urllib.request import urlopen

from slidebridge.remote.ssh import build_ssh_base_command
from slidebridge.remote.spec import RemotePath


def is_local_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, int(port))) != 0


def build_tunnel_command(
    remote: RemotePath,
    remote_command: str,
    local_host: str = "127.0.0.1",
    local_port: int = 7860,
    remote_host: str = "127.0.0.1",
    remote_port: int = 7860,
    ssh_port: int | None = None,
    identity_file: str | None = None,
    ssh_options: list[str] | None = None,
) -> list[str]:
    command = build_ssh_base_command(
        remote.host,
        user=remote.user,
        port=ssh_port or remote.ssh_port,
        identity_file=identity_file,
        ssh_options=ssh_options,
    )
    target = command.pop()
    command.extend(
        [
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-L",
            f"{local_host}:{int(local_port)}:{remote_host}:{int(remote_port)}",
            target,
            remote_command,
        ]
    )
    return command


def wait_for_http(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + max(0.1, float(timeout))
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                return 200 <= int(response.status) < 500
        except URLError:
            time.sleep(0.5)
        except OSError:
            time.sleep(0.5)
    return False
