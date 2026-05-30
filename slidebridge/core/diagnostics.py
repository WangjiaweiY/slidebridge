from __future__ import annotations

import importlib
import importlib.metadata as metadata
import platform
import sys
from pathlib import Path
from typing import Any


PACKAGE_CHECKS = [
    ("tiffslide", "tiffslide"),
    ("openslide-python", "openslide"),
    ("openslide-bin", None),
    ("Pillow", "PIL"),
    ("numpy", "numpy"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("typer", "typer"),
]


def package_status(distribution: str, module: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": distribution,
        "available": False,
        "version": None,
        "status": "missing",
        "notes": "",
    }
    try:
        result["version"] = metadata.version(distribution)
    except metadata.PackageNotFoundError:
        result["notes"] = "distribution not installed"
    except Exception as exc:  # pragma: no cover - defensive
        result["notes"] = f"version check error: {exc}"

    if module is None:
        if result["version"]:
            result["available"] = True
            result["status"] = "available"
        return result

    try:
        importlib.import_module(module)
    except Exception as exc:
        result["status"] = "error" if result["version"] else "missing"
        result["notes"] = str(exc)
        return result

    result["available"] = True
    result["status"] = "available"
    result["notes"] = "import ok"
    return result


def environment_report() -> dict[str, Any]:
    packages = [package_status(distribution, module) for distribution, module in PACKAGE_CHECKS]
    return {
        "python_executable": sys.executable,
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "packages": packages,
        "openslide_available": _is_available(packages, "openslide-python"),
        "tiffslide_available": _is_available(packages, "tiffslide"),
    }


def reader_statuses() -> dict[str, dict[str, Any]]:
    return {
        "tiffslide": _reader_status("tiffslide", "tiffslide"),
        "openslide": _reader_status("openslide-python", "openslide"),
        "image": _reader_status("Pillow", "PIL"),
    }


def _reader_status(distribution: str, module: str) -> dict[str, Any]:
    status = package_status(distribution, module)
    if status["available"]:
        notes = f"{distribution} {status['version'] or 'unknown'} import ok"
    elif status["status"] == "missing":
        notes = status["notes"] or f"{distribution} not installed"
    else:
        notes = status["notes"] or "import error"
    return {
        "available": bool(status["available"]),
        "status": status["status"],
        "version": status["version"],
        "notes": notes,
    }


def _is_available(packages: list[dict[str, Any]], name: str) -> bool:
    for package in packages:
        if package["name"] == name:
            return bool(package["available"])
    return False

