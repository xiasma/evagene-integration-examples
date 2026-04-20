from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from voice_driven_intake.audio_source import AudioFile
from voice_driven_intake.chunker import ChunkRange
from voice_driven_intake.transcription_gateway import TranscriptionRequest
from voice_driven_intake.whisper_transcriber import (
    TranscriberSettings,
    WhisperTranscriber,
)


@dataclass
class _FakeProbe:
    duration: int
    silences: list[tuple[int, int]] = field(default_factory=list)
    slices: list[tuple[Path, ChunkRange, Path]] = field(default_factory=list)

    def duration_ms(self, path: Path) -> int:
        _ = path
        return self.duration

    def silences_ms(
        self, path: Path, *, min_silence_ms: int, silence_threshold_dbfs: float
    ) -> list[tuple[int, int]]:
        _ = (path, min_silence_ms, silence_threshold_dbfs)
        return list(self.silences)

    def export_slice(self, path: Path, chunk: ChunkRange, destination: Path) -> None:
        self.slices.append((path, chunk, destination))
        destination.write_bytes(b"fake-wav")


@dataclass
class _FakeGateway:
    responses: list[str]
    requests: list[TranscriptionRequest] = field(default_factory=list)

    def transcribe(self, request: TranscriptionRequest) -> str:
        self.requests.append(request)
        return self.responses[len(self.requests) - 1]


def _audio(tmp_path: Path) -> AudioFile:
    path = tmp_path / "recording.wav"
    path.write_bytes(b"RIFF")
    return AudioFile(path=path, size_bytes=4, suffix=".wav")


def test_short_audio_transcribes_with_a_single_gateway_call(tmp_path: Path) -> None:
    probe = _FakeProbe(duration=5000)
    gateway = _FakeGateway(responses=["Hello, family history for Emma."])

    transcript = WhisperTranscriber(
        probe=probe, gateway=gateway, settings=TranscriberSettings(max_single_chunk_ms=10_000)
    ).transcribe(_audio(tmp_path), language="en")

    assert transcript == "Hello, family history for Emma."
    assert len(gateway.requests) == 1
    assert gateway.requests[0].language == "en"
    assert not probe.slices  # no chunking required


def test_long_audio_is_chunked_and_concatenated(tmp_path: Path) -> None:
    probe = _FakeProbe(duration=20_000, silences=[(9500, 10_500)])
    gateway = _FakeGateway(responses=["First half.", "Second half."])

    transcript = WhisperTranscriber(
        probe=probe,
        gateway=gateway,
        settings=TranscriberSettings(max_single_chunk_ms=15_000),
    ).transcribe(_audio(tmp_path), language=None)

    assert transcript == "First half. Second half."
    assert len(gateway.requests) == 2
    assert len(probe.slices) == 2
    # Each gateway upload targets the freshly exported slice, not the original file.
    uploaded_paths = [request.audio_path for request in gateway.requests]
    exported_paths = [destination for _, _, destination in probe.slices]
    assert uploaded_paths == exported_paths
    assert all(path.exists() is False for path in exported_paths)  # tmpdir cleaned up


def test_chunk_requests_carry_the_language_hint(tmp_path: Path) -> None:
    probe = _FakeProbe(duration=20_000, silences=[(9500, 10_500)])
    gateway = _FakeGateway(responses=["a", "b"])

    WhisperTranscriber(
        probe=probe,
        gateway=gateway,
        settings=TranscriberSettings(max_single_chunk_ms=15_000),
    ).transcribe(_audio(tmp_path), language="en")

    assert [request.language for request in gateway.requests] == ["en", "en"]


def test_audio_file_is_opened_by_gateway_not_by_transcriber(tmp_path: Path) -> None:
    probe = _FakeProbe(duration=5000)
    seen: list[Any] = []

    class _Recorder:
        def transcribe(self, request: TranscriptionRequest) -> str:
            # The gateway receives a path; it is the gateway's job to open it.
            seen.append(request.audio_path)
            return "ok"

    WhisperTranscriber(probe=probe, gateway=_Recorder()).transcribe(
        _audio(tmp_path), language=None
    )

    assert seen == [_audio(tmp_path).path]
