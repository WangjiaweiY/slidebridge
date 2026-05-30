from __future__ import annotations

from pathlib import Path

from slidebridge.core.protocol import Slide, SlideReader


class SlideOpenError(RuntimeError):
    """Raised when no registered reader can open a slide."""


_readers: dict[str, SlideReader] = {}
_defaults_registered = False


def register_reader(reader: SlideReader) -> None:
    """Register or replace a reader by name."""

    _readers[reader.name.lower()] = reader


def register_default_readers() -> None:
    global _defaults_registered
    if _defaults_registered:
        return
    from slidebridge.readers import ImageReader, OpenSlideReader, TiffSlideReader

    register_reader(TiffSlideReader())
    register_reader(OpenSlideReader())
    register_reader(ImageReader())
    _defaults_registered = True


def get_registered_readers() -> list[SlideReader]:
    register_default_readers()
    return sorted(_readers.values(), key=lambda item: item.priority, reverse=True)


def open_slide(path: str | Path, reader: str | None = None) -> Slide:
    register_default_readers()
    slide_path = Path(path)
    if not slide_path.exists():
        raise SlideOpenError(f"Slide path does not exist: {slide_path}")

    if reader:
        requested = reader.lower()
        candidates = [item for item in _readers.values() if item.name.lower() == requested]
        if not candidates:
            known = ", ".join(item.name for item in get_registered_readers()) or "none"
            raise SlideOpenError(f"Unknown reader: {reader}. Available readers: {known}")
    else:
        candidates = get_registered_readers()

    errors: list[str] = []
    for candidate in candidates:
        try:
            if not candidate.can_open(slide_path):
                errors.append(f"{candidate.name}: can_open returned False")
                continue
        except Exception as exc:  # pragma: no cover - defensive path
            errors.append(f"{candidate.name}: can_open failed: {exc}")
            continue

        try:
            return candidate.open(slide_path)
        except Exception as exc:
            errors.append(f"{candidate.name}: {exc}")

    tried = "; ".join(errors) if errors else "no readers were registered"
    raise SlideOpenError(f"No available reader could open this file. Tried: {tried}")
