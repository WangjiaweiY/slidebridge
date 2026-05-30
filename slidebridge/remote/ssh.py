from __future__ import annotations

import shlex
import shutil
from pathlib import Path


SSH_MISSING_MESSAGE = (
    "OpenSSH client was not found. Please install/enable OpenSSH Client on Windows "
    "or use another SSH client."
)


def check_ssh_available() -> bool:
    return shutil.which("ssh") is not None


def require_ssh_available() -> None:
    if not check_ssh_available():
        raise RuntimeError(SSH_MISSING_MESSAGE)


def build_ssh_base_command(
    host: str,
    user: str | None = None,
    port: int | None = None,
    identity_file: str | Path | None = None,
    ssh_options: list[str] | None = None,
) -> list[str]:
    command = ["ssh"]
    if port is not None:
        command.extend(["-p", str(int(port))])
    if identity_file is not None:
        command.extend(["-i", str(identity_file)])
    for option in ssh_options or []:
        if option:
            command.extend(shlex.split(option))
    command.append(f"{user}@{host}" if user else host)
    return command
