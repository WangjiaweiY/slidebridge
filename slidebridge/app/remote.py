from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from slidebridge.remote.commands import build_remote_slidebridge_command, quote_remote_arg
from slidebridge.remote.diagnostics import RemoteCommandResult, run_ssh_command
from slidebridge.remote.ssh import build_ssh_base_command, require_ssh_available


SLIDE_EXTENSIONS = {".svs", ".tif", ".tiff", ".ndpi", ".mrxs", ".png", ".jpg", ".jpeg"}
HEATMAP_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PATCH_EXTENSIONS = {".csv", ".h5", ".hdf5", ".json", ".npy", ".pt", ".pth"}
ANNOTATION_EXTENSIONS = {".geojson", ".json", ".xml"}


@dataclass(frozen=True)
class RemoteConnection:
    host: str
    user: str | None = None
    ssh_port: int | None = None
    identity_file: str | None = None
    ssh_options: list[str] = field(default_factory=list)
    remote_runner: str = "slidebridge"
    remote_workdir: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RemoteConnection":
        host = _clean_str(payload.get("host"))
        if not host:
            raise ValueError("Remote host is required.")
        ssh_port = _optional_int(payload.get("ssh_port"))
        return cls(
            host=host,
            user=_optional_str(payload.get("user")),
            ssh_port=ssh_port,
            identity_file=_optional_str(payload.get("identity_file")),
            ssh_options=_split_ssh_options(payload.get("ssh_options")),
            remote_runner=_remote_runner_from_payload(payload),
            remote_workdir=_optional_str(payload.get("remote_workdir")),
        )

    @property
    def target(self) -> str:
        return f"{self.user}@{self.host}" if self.user else self.host

    def ssh_base_command(self) -> list[str]:
        return build_ssh_base_command(
            self.host,
            user=self.user,
            port=self.ssh_port,
            identity_file=self.identity_file,
            ssh_options=self.ssh_options,
        )


def test_remote_connection(connection: RemoteConnection, timeout: float = 20.0) -> RemoteCommandResult:
    require_ssh_available()
    remote_command = build_remote_slidebridge_command(
        connection.remote_runner,
        ["version"],
        remote_workdir=connection.remote_workdir,
    )
    command = connection.ssh_base_command()
    command.append(remote_command)
    return run_ssh_command(command, timeout=timeout)


def test_ssh_connection(connection: RemoteConnection, timeout: float = 20.0) -> RemoteCommandResult:
    require_ssh_available()
    command = connection.ssh_base_command()
    command.append("printf 'slidebridge-ssh-ok\\n%s\\n' \"$HOME\"")
    return run_ssh_command(command, timeout=timeout)


def list_remote_directory(
    connection: RemoteConnection,
    remote_dir: str,
    limit: int = 500,
    timeout: float = 30.0,
) -> tuple[list[dict[str, Any]], RemoteCommandResult]:
    directory = _required_remote_path(remote_dir)
    command = connection.ssh_base_command()
    command.append(_remote_list_command(directory, limit=limit))
    result = run_ssh_command(command, timeout=timeout)
    if result.returncode != 0:
        return [], result
    entries = [_parse_find_line(line) for line in result.stdout.splitlines()]
    return [entry for entry in entries if entry is not None], result


def build_remote_view_cli_args(payload: dict[str, Any]) -> list[str]:
    connection = RemoteConnection.from_payload(payload)
    remote_path = _required_remote_path(payload.get("remote_path") or payload.get("remote_home") or "~")
    remote_spec = f"{connection.target}:{remote_path}"
    args = ["remote-view", remote_spec]
    if connection.ssh_port is not None:
        args.extend(["--ssh-port", str(connection.ssh_port)])
    if connection.identity_file:
        args.extend(["--identity-file", connection.identity_file])
    for option in connection.ssh_options:
        args.extend(["--ssh-option", option])
    if connection.remote_runner:
        args.extend(["--remote-runner", connection.remote_runner])
    if connection.remote_workdir:
        args.extend(["--remote-workdir", connection.remote_workdir])
    _append_option(args, "--local-host", payload.get("local_host"))
    _append_option(args, "--local-port", payload.get("local_port"))
    _append_option(args, "--remote-host", payload.get("remote_host"))
    _append_option(args, "--remote-port", payload.get("remote_port"))
    _append_option(args, "--patches", payload.get("patches"))
    _append_option(args, "--heatmap", payload.get("heatmap"))
    _append_option(args, "--raster-heatmap", payload.get("raster_heatmap"))
    for layer in _heatmap_layers(payload.get("raster_heatmap_layers")):
        args.extend(["--raster-heatmap-layer", layer])
    _append_option(args, "--annotations", payload.get("annotations"))
    _append_option(args, "--annotation-format", payload.get("annotation_format"))
    if _truthy(payload.get("recursive")):
        args.append("--recursive")
    _append_option(args, "--max-slides", payload.get("max_slides"))
    args.append("--no-open-browser")
    return args


def display_command(args: list[str]) -> str:
    return subprocess.list2cmdline(["slidebridge", *[str(item) for item in args]])


def process_command(args: list[str]) -> list[str]:
    import sys

    return [sys.executable, "-m", "slidebridge.cli", *[str(item) for item in args]]


def _remote_runner_from_payload(payload: dict[str, Any]) -> str:
    custom_runner = _optional_str(payload.get("remote_runner"))
    if custom_runner:
        return custom_runner
    conda_env_path = _optional_str(payload.get("conda_env_path"))
    if conda_env_path:
        python_path = f"{conda_env_path.rstrip('/')}/bin/python"
        return f"{quote_remote_arg(python_path)} -m slidebridge.cli"
    return "slidebridge"


def classify_remote_file(path: str, kind: str) -> bool:
    suffix = Path(str(path)).suffix.lower()
    if kind == "slide":
        return suffix in SLIDE_EXTENSIONS
    if kind == "heatmap":
        return suffix in HEATMAP_EXTENSIONS
    if kind == "patches":
        return suffix in PATCH_EXTENSIONS
    if kind == "annotation":
        return suffix in ANNOTATION_EXTENSIONS
    return False


def _remote_list_command(remote_dir: str, limit: int) -> str:
    directory = quote_remote_arg(remote_dir)
    count = max(1, min(int(limit), 5000))
    return (
        f"find {directory} -mindepth 1 -maxdepth 1 \\( -type d -o -type f \\) "
        f"-printf '%y\\t%p\\t%s\\t%TY-%Tm-%Td %TH:%TM\\n' "
        f"| sort | head -n {count}"
    )


def _parse_find_line(line: str) -> dict[str, Any] | None:
    parts = line.split("\t")
    if len(parts) < 4:
        return None
    kind_code, path, size, modified = parts[0], parts[1], parts[2], parts[3]
    kind = "directory" if kind_code == "d" else "file"
    entry = {
        "kind": kind,
        "path": path,
        "name": Path(path).name or path,
        "size": _optional_int(size),
        "modified": modified,
        "is_slide": False,
        "is_heatmap": False,
        "is_patches": False,
        "is_annotation": False,
    }
    if kind == "file":
        entry["is_slide"] = classify_remote_file(path, "slide")
        entry["is_heatmap"] = classify_remote_file(path, "heatmap")
        entry["is_patches"] = classify_remote_file(path, "patches")
        entry["is_annotation"] = classify_remote_file(path, "annotation")
    return entry


def _heatmap_layers(raw_layers: Any) -> list[str]:
    layers: list[str] = []
    if not isinstance(raw_layers, list):
        return layers
    for item in raw_layers:
        if isinstance(item, str):
            text = item.strip()
            if text:
                layers.append(text)
            continue
        if not isinstance(item, dict):
            continue
        path = _optional_str(item.get("path"))
        if not path:
            continue
        name = _optional_str(item.get("name"))
        layers.append(f"{name}={path}" if name else path)
    return layers


def _append_option(args: list[str], name: str, value: Any) -> None:
    text = _optional_str(value)
    if text is not None:
        args.extend([name, text])


def _required_remote_path(value: Any) -> str:
    text = _clean_str(value)
    if not text:
        raise ValueError("Remote path is required.")
    if not (text.startswith("/") or text.startswith("~")):
        raise ValueError("Remote path must start with '/' or '~'.")
    return text


def _split_ssh_options(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _optional_str(value: Any) -> str | None:
    text = _clean_str(value)
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}
