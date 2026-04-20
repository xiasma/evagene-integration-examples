"""Read a transcript from a file path or from a stdin-like stream."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO


class TranscriptError(ValueError):
    """Raised when no usable transcript can be read."""


def read_from_path(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TranscriptError(f"Could not read transcript {path}: {exc}") from exc
    return _require_non_empty(text, source=str(path))


def read_from_stream(stream: TextIO) -> str:
    return _require_non_empty(stream.read(), source="stdin")


def _require_non_empty(text: str, *, source: str) -> str:
    if not text.strip():
        raise TranscriptError(f"Transcript from {source} was empty.")
    return text
