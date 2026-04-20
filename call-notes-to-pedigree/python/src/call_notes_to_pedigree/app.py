"""Composition root and runtime entry point."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TextIO

from .anthropic_extractor import (
    AnthropicExtractor,
    AnthropicGateway,
    LlmGateway,
    LlmUnavailableError,
)
from .config import Config, ConfigError, load_config
from .evagene_client import EvageneApi, EvageneApiError, EvageneClient
from .evagene_writer import EvageneWriter
from .extracted_family import ExtractedFamily
from .extraction_schema import SYSTEM_PROMPT, ExtractionSchemaError, build_tool_schema
from .http_gateway import HttpxGateway
from .presenter import present
from .transcript_source import TranscriptError, read_from_path, read_from_stream

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_SCHEMA = 70


def run(
    argv: list[str],
    env: dict[str, str],
    stdin: TextIO,
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

    try:
        transcript = _read_transcript(config.transcript_path, stdin)
    except TranscriptError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway = _anthropic_gateway(config)
    family, extraction_error = _extract(gateway, transcript, config.model)
    if extraction_error is not None:
        stderr.write(f"error: {extraction_error.message}\n")
        return extraction_error.exit_code

    assert family is not None
    present(family, stdout)

    if not config.commit:
        return EXIT_OK
    return _commit(family, config, stdout, stderr)


def _read_transcript(path: Path | None, stdin: TextIO) -> str:
    return read_from_path(path) if path is not None else read_from_stream(stdin)


def _print_prompt(stdout: TextIO) -> None:
    stdout.write("System prompt:\n")
    stdout.write(SYSTEM_PROMPT)
    stdout.write("\n\nTool schema:\n")
    stdout.write(json.dumps(build_tool_schema(), indent=2))
    stdout.write("\n")


class _ExtractionFailure:
    __slots__ = ("exit_code", "message")

    def __init__(self, exit_code: int, message: str) -> None:
        self.exit_code = exit_code
        self.message = message


def _extract(
    gateway: LlmGateway,
    transcript: str,
    model: str,
) -> tuple[ExtractedFamily | None, _ExtractionFailure | None]:
    extractor = AnthropicExtractor(gateway, model=model)
    try:
        return extractor.extract(transcript), None
    except LlmUnavailableError as error:
        return None, _ExtractionFailure(EXIT_UNAVAILABLE, str(error))
    except ExtractionSchemaError as error:
        return None, _ExtractionFailure(EXIT_SCHEMA, str(error))


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
    sys.exit(run(sys.argv[1:], dict(os.environ), sys.stdin, sys.stdout, sys.stderr))
