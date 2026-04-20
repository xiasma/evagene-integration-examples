"""Turn an :class:`AudioFile` into a transcript using probe + chunker + gateway.

Audio longer than ``max_single_chunk_ms`` is split at silence midpoints
(see :mod:`chunker`) so each chunk fits under Whisper's single-request
byte ceiling. The transcript of each chunk is concatenated into the
final result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from .audio_probe import AudioProbe
from .audio_source import AudioFile
from .chunker import ChunkRange, plan_chunks
from .transcription_gateway import TranscriptionGateway, TranscriptionRequest

DEFAULT_SINGLE_CHUNK_MS = 20 * 60 * 1000
DEFAULT_MIN_SILENCE_MS = 1000
DEFAULT_SILENCE_THRESHOLD_DBFS = -40.0


@dataclass(frozen=True)
class TranscriberSettings:
    max_single_chunk_ms: int = DEFAULT_SINGLE_CHUNK_MS
    min_silence_ms: int = DEFAULT_MIN_SILENCE_MS
    silence_threshold_dbfs: float = DEFAULT_SILENCE_THRESHOLD_DBFS


_DEFAULT_SETTINGS = TranscriberSettings()


class WhisperTranscriber:
    def __init__(
        self,
        *,
        probe: AudioProbe,
        gateway: TranscriptionGateway,
        settings: TranscriberSettings = _DEFAULT_SETTINGS,
    ) -> None:
        self._probe = probe
        self._gateway = gateway
        self._settings = settings

    def transcribe(self, audio: AudioFile, *, language: str | None) -> str:
        duration = self._probe.duration_ms(audio.path)
        if duration <= self._settings.max_single_chunk_ms:
            return self._gateway.transcribe(
                TranscriptionRequest(audio_path=audio.path, language=language)
            )
        return self._transcribe_in_chunks(audio, duration=duration, language=language)

    def _transcribe_in_chunks(
        self, audio: AudioFile, *, duration: int, language: str | None
    ) -> str:
        silences = self._probe.silences_ms(
            audio.path,
            min_silence_ms=self._settings.min_silence_ms,
            silence_threshold_dbfs=self._settings.silence_threshold_dbfs,
        )
        chunks = plan_chunks(
            duration_ms=duration,
            silences_ms=silences,
            max_chunk_ms=self._settings.max_single_chunk_ms,
        )
        with TemporaryDirectory(prefix="voice-intake-") as tmpdir:
            parts = [
                self._transcribe_chunk(audio, chunk, Path(tmpdir), index, language)
                for index, chunk in enumerate(chunks)
            ]
        return " ".join(part.strip() for part in parts if part.strip())

    def _transcribe_chunk(
        self,
        audio: AudioFile,
        chunk: ChunkRange,
        tmpdir: Path,
        index: int,
        language: str | None,
    ) -> str:
        slice_path = tmpdir / f"chunk-{index:04d}.wav"
        self._probe.export_slice(audio.path, chunk, slice_path)
        return self._gateway.transcribe(
            TranscriptionRequest(audio_path=slice_path, language=language)
        )
