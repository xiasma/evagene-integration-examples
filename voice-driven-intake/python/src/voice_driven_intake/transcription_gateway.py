"""Abstraction for a speech-to-text service plus an OpenAI Whisper implementation.

The gateway takes a path to an audio file and returns a plain-text
transcript. Language is a hint; passing ``None`` lets the service
auto-detect. Everything else -- chunking long files, merging partial
transcripts -- lives in :mod:`whisper_transcriber`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openai import NOT_GIVEN, OpenAI, OpenAIError

DEFAULT_WHISPER_MODEL = "whisper-1"


class TranscriptionUnavailableError(RuntimeError):
    """Raised when the transcription service is unreachable or rejects the file."""


@dataclass(frozen=True)
class TranscriptionRequest:
    audio_path: Path
    language: str | None


class TranscriptionGateway(Protocol):
    def transcribe(self, request: TranscriptionRequest) -> str: ...


class OpenAiWhisperGateway:
    """Concrete :class:`TranscriptionGateway` backed by the OpenAI Whisper API."""

    def __init__(self, *, api_key: str, model: str = DEFAULT_WHISPER_MODEL) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def transcribe(self, request: TranscriptionRequest) -> str:
        language = request.language if request.language is not None else NOT_GIVEN
        try:
            with request.audio_path.open("rb") as handle:
                response = self._client.audio.transcriptions.create(
                    model=self._model,
                    file=handle,
                    language=language,
                    response_format="text",
                )
        except OpenAIError as exc:
            raise TranscriptionUnavailableError(
                f"Whisper API call failed: {exc}"
            ) from exc
        except OSError as exc:
            raise TranscriptionUnavailableError(
                f"Could not read audio file {request.audio_path}: {exc}"
            ) from exc
        return _as_text(response)


def _as_text(response: object) -> str:
    if isinstance(response, str):
        return response
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    raise TranscriptionUnavailableError(
        "Whisper response did not contain a text transcript."
    )
