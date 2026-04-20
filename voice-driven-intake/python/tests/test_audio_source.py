from pathlib import Path

import pytest

from voice_driven_intake.audio_source import AudioSourceError, open_audio


def _write_bytes(path: Path, blob: bytes) -> Path:
    path.write_bytes(blob)
    return path


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(AudioSourceError, match="not found"):
        open_audio(tmp_path / "absent.wav", max_size_bytes=1024)


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    path = _write_bytes(tmp_path / "recording.txt", b"not audio")

    with pytest.raises(AudioSourceError, match="Unsupported"):
        open_audio(path, max_size_bytes=1024)


def test_empty_file_raises(tmp_path: Path) -> None:
    path = _write_bytes(tmp_path / "recording.wav", b"")

    with pytest.raises(AudioSourceError, match="empty"):
        open_audio(path, max_size_bytes=1024)


def test_oversized_file_raises(tmp_path: Path) -> None:
    path = _write_bytes(tmp_path / "recording.wav", b"x" * 2048)

    with pytest.raises(AudioSourceError, match="ceiling"):
        open_audio(path, max_size_bytes=1024)


def test_extension_is_case_insensitive(tmp_path: Path) -> None:
    path = _write_bytes(tmp_path / "recording.WAV", b"RIFF....WAVEfmt ")

    audio = open_audio(path, max_size_bytes=10_000)

    assert audio.suffix == ".wav"
    assert audio.size_bytes == path.stat().st_size
