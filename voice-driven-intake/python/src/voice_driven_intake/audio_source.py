"""Validate that an input file looks like an audio recording we can handle.

No decoding happens here -- just path, extension, and byte-size checks.
Duration is probed elsewhere (:mod:`audio_probe`) so this module stays
pure and side-effect-free apart from the ``stat`` call.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".wav", ".m4a", ".mp3", ".webm", ".ogg"})


class AudioSourceError(ValueError):
    """Raised when the audio file is missing, the wrong format, or too large."""


@dataclass(frozen=True)
class AudioFile:
    path: Path
    size_bytes: int
    suffix: str


def open_audio(path: Path, *, max_size_bytes: int) -> AudioFile:
    """Return an :class:`AudioFile` for ``path`` after validation.

    Parameters
    ----------
    path
        Location of the recording.
    max_size_bytes
        Hard ceiling on the file size. Recordings above this are rejected
        before any transcoding or upload is attempted.
    """
    if not path.is_file():
        raise AudioSourceError(f"Audio file not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise AudioSourceError(
            f"Unsupported audio format {suffix!r}. Supported: {supported}."
        )

    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise AudioSourceError(f"Audio file is empty: {path}")
    if size_bytes > max_size_bytes:
        raise AudioSourceError(
            f"Audio file is {size_bytes} bytes; configured ceiling is {max_size_bytes}."
        )

    return AudioFile(path=path, size_bytes=size_bytes, suffix=suffix)
