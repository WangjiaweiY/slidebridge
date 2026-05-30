from __future__ import annotations

import subprocess
from dataclasses import dataclass


REMOTE_INSTALL_HINT = (
    "Remote SlideBridge was not found or failed to run. Install it on the remote machine, "
    "or pass --remote-runner, for example: conda run -n slidebridge slidebridge"
)


@dataclass(frozen=True)
class RemoteCommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def run_ssh_command(command: list[str], timeout: float | None = None) -> RemoteCommandResult:
    completed = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return RemoteCommandResult(
        command=command,
        returncode=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
