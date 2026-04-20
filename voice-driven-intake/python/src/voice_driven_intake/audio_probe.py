"""Probe audio files for duration and silence boundaries, and cut slices.

The :class:`AudioProbe` protocol is the seam between :mod:`whisper_transcriber`
and the heavyweight ``pydub`` / ``ffmpeg`` stack. Tests supply a fake probe
so the orchestration code can be exercised without decoding real audio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydub import AudioSegment
from pydub.silence import detect_silence

from .chunker import ChunkRange


class AudioProbeError(RuntimeError):
    """Raised when the underlying audio library cannot read the file."""


class AudioProbe(Protocol):
    def duration_ms(self, path: Path) -> int: ...

    def silences_ms(
        self, path: Path, *, min_silence_ms: int, silence_threshold_dbfs: float
    ) -> list[tuple[int, int]]: ...

    def export_slice(self, path: Path, chunk: ChunkRange, destination: Path) -> None: ...


class PydubProbe:
    """Concrete :class:`AudioProbe` backed by ``pydub`` (requires ``ffmpeg`` on PATH)."""

    def duration_ms(self, path: Path) -> int:
        return len(self._load(path))

    def silences_ms(
        self, path: Path, *, min_silence_ms: int, silence_threshold_dbfs: float
    ) -> list[tuple[int, int]]:
        segment = self._load(path)
        ranges = detect_silence(
            segment,
            min_silence_len=min_silence_ms,
            silence_thresh=silence_threshold_dbfs,
        )
        return [(int(start), int(end)) for start, end in ranges]

    def export_slice(self, path: Path, chunk: ChunkRange, destination: Path) -> None:
        segment = self._load(path)
        segment[chunk.start_ms : chunk.end_ms].export(str(destination), format="wav")

    def _load(self, path: Path) -> AudioSegment:
        try:
            return AudioSegment.from_file(str(path))
        except (OSError, ValueError) as exc:
            raise AudioProbeError(f"Could not decode audio {path}: {exc}") from exc
