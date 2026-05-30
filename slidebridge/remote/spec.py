from __future__ import annotations

import re
from dataclasses import dataclass


_REMOTE_PATTERN = re.compile(r"^(?:(?P<user>[^@\s:/\\]+)@)?(?P<host>[^:\s/\\]+):(?P<path>.+)$")
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True)
class RemotePath:
    user: str | None
    host: str
    path: str
    ssh_port: int | None = None

    @property
    def target(self) -> str:
        return f"{self.user}@{self.host}" if self.user else self.host


def is_remote_spec(value: str) -> bool:
    text = str(value or "").strip()
    if _WINDOWS_DRIVE_PATTERN.match(text):
        return False
    match = _REMOTE_PATTERN.match(text)
    if match is None:
        return False
    path = match.group("path")
    return path.startswith("/") or path.startswith("~")


def parse_remote_path(value: str) -> RemotePath:
    text = str(value or "").strip()
    if _WINDOWS_DRIVE_PATTERN.match(text):
        raise ValueError(f"Windows local paths are not remote specs: {value}")
    match = _REMOTE_PATTERN.match(text)
    if match is None:
        raise ValueError("Remote path must use [user@]host:/absolute/path or [user@]host:~/path.")
    path = match.group("path")
    if not (path.startswith("/") or path.startswith("~")):
        raise ValueError("Remote path must start with '/' or '~'. Use user@host:/absolute/path/to/slide.svs.")
    return RemotePath(
        user=match.group("user"),
        host=match.group("host"),
        path=path,
    )
