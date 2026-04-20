"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from typing import TextIO

from .config import Config, ConfigError, load_config
from .evagene_client import ApiError, EvageneClient
from .http_gateway import HttpxGateway
from .orchestrator import build_briefing
from .pdf_builder import ReportLabPdfSink

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_INTERNAL = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ, today=date.today())
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway = HttpxGateway()
    try:
        return _render(config, gateway, stdout, stderr)
    finally:
        gateway.close()


def _render(
    config: Config,
    gateway: HttpxGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    client = EvageneClient(base_url=config.base_url, api_key=config.api_key, http=gateway)
    sink = ReportLabPdfSink(config.output_path)
    try:
        build_briefing(config, client, sink, now=datetime.now)
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE
    except OSError as error:
        stderr.write(f"error: could not write {config.output_path}: {error}\n")
        return EXIT_INTERNAL

    stdout.write(f"Wrote {config.output_path}\n")
    return EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
