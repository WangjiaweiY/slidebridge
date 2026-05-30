from __future__ import annotations

from pathlib import Path


SUPPORTED_WSI_EXTENSIONS = {
    ".svs",
    ".tif",
    ".tiff",
    ".ndpi",
    ".mrxs",
    ".scn",
    ".svslide",
}

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
}


def ensure_parent(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def iter_slide_paths(path: str | Path, recursive: bool = False) -> list[Path]:
    root = Path(path)
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {root}")

    pattern = "**/*" if recursive else "*"
    paths = [
        item
        for item in root.glob(pattern)
        if item.is_file() and item.suffix.lower() in SUPPORTED_WSI_EXTENSIONS
    ]
    return sorted(paths)

