from __future__ import annotations

import secrets
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from slidebridge.app.remote import build_remote_view_cli_args, display_command, process_command


@dataclass
class ViewerSession:
    id: str
    mode: str
    viewer_url: str
    display_command: str
    process_command: list[str]
    started_at: float
    process: subprocess.Popen | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        if self.process is None:
            return "prepared"
        return "running" if self.process.poll() is None else "stopped"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "status": self.status,
            "viewer_url": self.viewer_url,
            "command": self.display_command,
            "started_at": self.started_at,
            "slide": self.payload.get("remote_path") or self.payload.get("remote_home") or self.payload.get("slide_path"),
        }


class ViewerSessionManager:
    def __init__(self) -> None:
        self._session: ViewerSession | None = None

    def prepare_remote(self, payload: dict[str, Any]) -> ViewerSession:
        cli_args = build_remote_view_cli_args(payload)
        session = ViewerSession(
            id=_session_id(),
            mode="remote",
            viewer_url=_viewer_url(payload),
            display_command=display_command(cli_args),
            process_command=process_command(cli_args),
            started_at=time.time(),
            payload=dict(payload),
        )
        return session

    def launch_remote(self, payload: dict[str, Any]) -> ViewerSession:
        self.stop_current()
        session = self.prepare_remote(payload)
        session.process = subprocess.Popen(session.process_command)
        self._session = session
        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        return [self._session.to_dict()] if self._session is not None else []

    def get(self, session_id: str) -> ViewerSession:
        if self._session is not None and self._session.id == session_id:
            return self._session
        raise KeyError(f"Unknown active viewer: {session_id}")

    def stop(self, session_id: str) -> ViewerSession:
        session = self.get(session_id)
        self._stop_session(session)
        return session

    def stop_current(self) -> ViewerSession | None:
        session = self._session
        if session is None:
            return None
        self._stop_session(session)
        return session

    def _stop_session(self, session: ViewerSession) -> None:
        process = session.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def _viewer_url(payload: dict[str, Any]) -> str:
    host = str(payload.get("local_host") or "127.0.0.1").strip() or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = int(payload.get("local_port") or 7860)
    return f"http://{host}:{port}"


def _session_id() -> str:
    return f"viewer-{secrets.token_hex(6)}"
