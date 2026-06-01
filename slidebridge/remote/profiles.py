from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from slidebridge.remote.spec import RemotePath


PROFILE_ENV_VAR = "SLIDEBRIDGE_REMOTE_PROFILES"


@dataclass(frozen=True)
class RemoteProfile:
    name: str
    host: str
    user: str | None = None
    ssh_port: int | None = None
    identity_file: str | None = None
    ssh_options: list[str] = field(default_factory=list)
    remote_runner: str = "slidebridge"
    remote_workdir: str | None = None
    root: str | None = None
    local_host: str = "127.0.0.1"
    local_port: int = 7860
    remote_host: str = "127.0.0.1"
    remote_port: int = 7860

    @property
    def target(self) -> str:
        return f"{self.user}@{self.host}" if self.user else self.host

    def to_remote_path(self, server_path: str | None = None) -> RemotePath:
        return RemotePath(
            user=self.user,
            host=self.host,
            path=self.resolve_server_path(server_path),
            ssh_port=self.ssh_port,
        )

    def resolve_server_path(self, server_path: str | None = None) -> str:
        text = str(server_path or "").strip()
        if not text:
            if self.root:
                return self.root
            raise ValueError(f"Profile '{self.name}' has no root path. Pass an absolute remote path.")
        if text.startswith("/") or text.startswith("~"):
            return text
        if not self.root:
            raise ValueError(
                f"Remote path '{text}' is relative, but profile '{self.name}' has no root path. "
                "Use an absolute server path or set --root on the profile."
            )
        return f"{self.root.rstrip('/')}/{text.lstrip('/')}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "user": self.user,
            "ssh_port": self.ssh_port,
            "identity_file": self.identity_file,
            "ssh_options": list(self.ssh_options),
            "remote_runner": self.remote_runner,
            "remote_workdir": self.remote_workdir,
            "root": self.root,
            "local_host": self.local_host,
            "local_port": self.local_port,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RemoteProfile":
        name = str(payload.get("name") or "").strip()
        host = str(payload.get("host") or "").strip()
        if not name:
            raise ValueError("Remote profile name is required.")
        if not host:
            raise ValueError(f"Remote profile '{name}' is missing host.")
        return cls(
            name=name,
            host=host,
            user=_optional_str(payload.get("user")),
            ssh_port=_optional_int(payload.get("ssh_port")),
            identity_file=_optional_str(payload.get("identity_file")),
            ssh_options=[str(item) for item in payload.get("ssh_options") or []],
            remote_runner=str(payload.get("remote_runner") or "slidebridge"),
            remote_workdir=_optional_str(payload.get("remote_workdir")),
            root=_optional_str(payload.get("root")),
            local_host=str(payload.get("local_host") or "127.0.0.1"),
            local_port=int(payload.get("local_port") or 7860),
            remote_host=str(payload.get("remote_host") or "127.0.0.1"),
            remote_port=int(payload.get("remote_port") or 7860),
        )


def profile_config_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    env_path = os.environ.get(PROFILE_ENV_VAR)
    if env_path:
        return Path(env_path)
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "slidebridge" / "remote_profiles.json"


def load_profiles(path: str | Path | None = None) -> dict[str, RemoteProfile]:
    config_path = profile_config_path(path)
    if not config_path.exists():
        return {}
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("profiles", [])
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    profiles: dict[str, RemoteProfile] = {}
    for item in items:
        profile = RemoteProfile.from_dict(item)
        profiles[profile.name] = profile
    return profiles


def save_profiles(profiles: dict[str, RemoteProfile], path: str | Path | None = None) -> Path:
    config_path = profile_config_path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "profiles": [profile.to_dict() for profile in sorted(profiles.values(), key=lambda item: item.name)],
    }
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return config_path


def upsert_profile(profile: RemoteProfile, path: str | Path | None = None) -> Path:
    profiles = load_profiles(path)
    profiles[profile.name] = profile
    return save_profiles(profiles, path)


def delete_profile(name: str, path: str | Path | None = None) -> Path:
    profiles = load_profiles(path)
    if name not in profiles:
        raise KeyError(f"Unknown remote profile: {name}")
    del profiles[name]
    return save_profiles(profiles, path)


def get_profile(name: str, path: str | Path | None = None) -> RemoteProfile:
    profiles = load_profiles(path)
    try:
        return profiles[name]
    except KeyError as exc:
        available = ", ".join(sorted(profiles)) or "none"
        raise KeyError(f"Unknown remote profile: {name}. Available profiles: {available}") from exc


def resolve_profile_target(
    value: str,
    profile_name: str | None = None,
    path: str | Path | None = None,
) -> tuple[RemotePath, RemoteProfile | None]:
    profiles = load_profiles(path)
    text = str(value or "").strip()
    if profile_name:
        profile = get_profile(profile_name, path)
        server_path = text
        if text == profile.name:
            server_path = ""
        return profile.to_remote_path(server_path), profile
    if ":" in text:
        prefix, server_path = text.split(":", 1)
        if prefix in profiles:
            profile = profiles[prefix]
            return profile.to_remote_path(server_path), profile
    raise KeyError("No matching remote profile")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
