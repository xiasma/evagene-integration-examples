"""Composition root and runtime entry point."""

from __future__ import annotations

import json
import os
import sys
from typing import TextIO

from .audio_probe import AudioProbe, AudioProbeError, PydubProbe
from .audio_source import AudioFile, AudioSourceError, open_audio
from .config import Config, ConfigError, load_config
from .evagene_client import EvageneApi, EvageneApiError, EvageneClient
from .evagene_writer import EvageneWriter
from .extracted_family import ExtractedFamily
from .extraction_schema import SYSTEM_PROMPT, ExtractionSchemaError, build_tool_schema
from .http_gateway import HttpxGateway
from .presenter import present
from .text_extractor import AnthropicGateway, LlmGateway, LlmUnavailableError, TextExtractor
from .transcription_gateway import (
    OpenAiWhisperGateway,
    TranscriptionGateway,
    TranscriptionUnavailableError,
)
from .whisper_transcriber import WhisperTranscriber

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_SCHEMA = 70
EXIT_AUDIO = 71


def run(
    argv: list[str],
    env: dict[str, str],
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        config = load_config(argv, env)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    if config.show_prompt:
        _print_prompt(stdout)
        return EXIT_OK

    probe = PydubProbe()
    return _run_pipeline(config, probe, stdout, stderr)


def _run_pipeline(
    config: Config,
    probe: AudioProbe,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    audio_or_exit = _open_audio(config, probe, stderr)
    if isinstance(audio_or_exit, int):
        return audio_or_exit
    audio = audio_or_exit

    transcript_or_exit = _transcribe(config, audio, probe, stderr)
    if isinstance(transcript_or_exit, int):
        return transcript_or_exit
    transcript = transcript_or_exit

    if config.show_transcript:
        stdout.write(transcript)
        stdout.write("\n")
        return EXIT_OK

    family_or_exit = _extract(config, transcript, stderr)
    if isinstance(family_or_exit, int):
        return family_or_exit
    family = family_or_exit

    present(family, stdout)
    if not config.commit:
        return EXIT_OK
    return _commit(family, config, stdout, stderr)


def _open_audio(
    config: Config, probe: AudioProbe, stderr: TextIO
) -> AudioFile | int:
    assert config.audio_path is not None
    try:
        audio = open_audio(config.audio_path, max_size_bytes=config.max_file_bytes)
    except AudioSourceError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_AUDIO
    try:
        duration_ms = probe.duration_ms(audio.path)
    except AudioProbeError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_AUDIO
    max_ms = config.max_duration_s * 1000
    if duration_ms > max_ms:
        stderr.write(
            f"error: Audio duration {duration_ms // 1000}s exceeds the "
            f"{config.max_duration_s}s cap (set VOICE_INTAKE_MAX_DURATION_S to raise it).\n"
        )
        return EXIT_AUDIO
    return audio


def _transcribe(
    config: Config, audio: AudioFile, probe: AudioProbe, stderr: TextIO
) -> str | int:
    gateway = _transcription_gateway(config)
    transcriber = WhisperTranscriber(probe=probe, gateway=gateway)
    try:
        return transcriber.transcribe(audio, language=config.language)
    except TranscriptionUnavailableError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE
    except AudioProbeError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_AUDIO


def _extract(
    config: Config, transcript: str, stderr: TextIO
) -> ExtractedFamily | int:
    gateway = _anthropic_gateway(config)
    extractor = TextExtractor(gateway, model=config.model)
    try:
        return extractor.extract(transcript)
    except LlmUnavailableError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE
    except ExtractionSchemaError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_SCHEMA


def _commit(
    family: ExtractedFamily,
    config: Config,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    http = HttpxGateway()
    try:
        client = _evagene_client(config, http)
        try:
            result = EvageneWriter(client).write(family)
        except EvageneApiError as error:
            stderr.write(f"error: {error}\n")
            return EXIT_UNAVAILABLE
    finally:
        http.close()

    stdout.write(f"\nCreated pedigree {result.pedigree_id}\n")
    stdout.write(f"{config.evagene_base_url.rstrip('/')}/pedigrees/{result.pedigree_id}\n")
    return EXIT_OK


def _print_prompt(stdout: TextIO) -> None:
    stdout.write("System prompt:\n")
    stdout.write(SYSTEM_PROMPT)
    stdout.write("\n\nTool schema:\n")
    stdout.write(json.dumps(build_tool_schema(), indent=2))
    stdout.write("\n")


def _transcription_gateway(config: Config) -> TranscriptionGateway:
    assert config.openai_api_key is not None
    return OpenAiWhisperGateway(api_key=config.openai_api_key)


def _anthropic_gateway(config: Config) -> LlmGateway:
    assert config.anthropic_api_key is not None
    return AnthropicGateway(api_key=config.anthropic_api_key)


def _evagene_client(config: Config, http: HttpxGateway) -> EvageneApi:
    assert config.evagene_api_key is not None
    return EvageneClient(
        base_url=config.evagene_base_url,
        api_key=config.evagene_api_key,
        http=http,
    )


def main() -> None:
    sys.exit(run(sys.argv[1:], dict(os.environ), sys.stdout, sys.stderr))
