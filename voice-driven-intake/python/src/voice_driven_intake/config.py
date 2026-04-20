"""Immutable configuration for the voice-driven-intake CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .text_extractor import DEFAULT_MODEL

DEFAULT_BASE_URL = "https://evagene.net"
DEFAULT_MAX_DURATION_S = 30 * 60
DEFAULT_MAX_FILE_MB = 200


class ConfigError(ValueError):
    """Raised when CLI or environment configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    audio_path: Path | None
    commit: bool
    show_prompt: bool
    show_transcript: bool
    language: str | None
    model: str
    max_duration_s: int
    max_file_bytes: int
    anthropic_api_key: str | None
    openai_api_key: str | None
    evagene_api_key: str | None
    evagene_base_url: str


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    args = _parse_args(argv)
    model = args.model or DEFAULT_MODEL
    max_duration_s = _resolve_max_duration(env)
    max_file_bytes = DEFAULT_MAX_FILE_MB * 1024 * 1024
    base_url = _resolve_base_url(env)

    if args.show_prompt:
        return Config(
            audio_path=_as_path(args.audio_file),
            commit=False,
            show_prompt=True,
            show_transcript=False,
            language=args.language,
            model=model,
            max_duration_s=max_duration_s,
            max_file_bytes=max_file_bytes,
            anthropic_api_key=None,
            openai_api_key=None,
            evagene_api_key=None,
            evagene_base_url=base_url,
        )

    audio_path = _require_audio_path(args.audio_file)
    openai_api_key = _require_env(env, "OPENAI_API_KEY")

    if args.show_transcript:
        return Config(
            audio_path=audio_path,
            commit=False,
            show_prompt=False,
            show_transcript=True,
            language=args.language,
            model=model,
            max_duration_s=max_duration_s,
            max_file_bytes=max_file_bytes,
            anthropic_api_key=None,
            openai_api_key=openai_api_key,
            evagene_api_key=None,
            evagene_base_url=base_url,
        )

    anthropic_api_key = _require_env(env, "ANTHROPIC_API_KEY")
    evagene_api_key = _resolve_evagene_key(env, commit=args.commit)

    return Config(
        audio_path=audio_path,
        commit=args.commit,
        show_prompt=False,
        show_transcript=False,
        language=args.language,
        model=model,
        max_duration_s=max_duration_s,
        max_file_bytes=max_file_bytes,
        anthropic_api_key=anthropic_api_key,
        openai_api_key=openai_api_key,
        evagene_api_key=evagene_api_key,
        evagene_base_url=base_url,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="voice-intake",
        description=(
            "Transcribe a recorded family history with OpenAI Whisper, extract a "
            "structured family via Claude, and optionally create the pedigree in "
            "Evagene."
        ),
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        default=None,
        help="Path to the audio recording (.wav, .m4a, .mp3, .webm, .ogg).",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="After extraction, create the pedigree in Evagene.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Whisper language hint (ISO-639-1, e.g. 'en'). Auto-detect if omitted.",
    )
    parser.add_argument(
        "--show-transcript",
        action="store_true",
        help="Transcribe and print the transcript only; skip extraction and commit.",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the system prompt and tool schema and exit. No network calls.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Override the Claude model (default: {DEFAULT_MODEL}).",
    )
    return parser.parse_args(argv)


def _as_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _require_audio_path(value: str | None) -> Path:
    if not value:
        raise ConfigError("An audio file path is required (positional argument).")
    return Path(value)


def _require_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} environment variable is required.")
    return value


def _resolve_evagene_key(env: Mapping[str, str], *, commit: bool) -> str | None:
    if not commit:
        return None
    value = env.get("EVAGENE_API_KEY", "").strip()
    if not value:
        raise ConfigError(
            "--commit requires the EVAGENE_API_KEY environment variable to be set."
        )
    return value


def _resolve_base_url(env: Mapping[str, str]) -> str:
    return env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL


def _resolve_max_duration(env: Mapping[str, str]) -> int:
    raw = env.get("VOICE_INTAKE_MAX_DURATION_S", "").strip()
    if not raw:
        return DEFAULT_MAX_DURATION_S
    try:
        seconds = int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"VOICE_INTAKE_MAX_DURATION_S must be a positive integer, got {raw!r}."
        ) from exc
    if seconds <= 0:
        raise ConfigError("VOICE_INTAKE_MAX_DURATION_S must be a positive integer.")
    return seconds
