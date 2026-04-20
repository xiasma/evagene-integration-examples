"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import TextIO

from .config import Config, ConfigError, load_config
from .csv_writer import CsvWriter
from .evagene_client import EvageneClient
from .gedcom_scanner import GedcomFile, GedcomScanner, ScannerError
from .http_gateway import HttpxGateway
from .row_result import RowResult
from .triage_service import TriageOptions, TriageService

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_INVALID_INPUT = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    scanner = GedcomScanner(config.input_dir)
    try:
        files = list(scanner.scan())
    except ScannerError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_INVALID_INPUT

    gateway = HttpxGateway()
    try:
        return _triage(config, files, gateway, stdout)
    finally:
        gateway.close()


def _triage(
    config: Config,
    files: list[GedcomFile],
    gateway: HttpxGateway,
    stdout: TextIO,
) -> int:
    client = EvageneClient(base_url=config.base_url, api_key=config.api_key, http=gateway)
    service = TriageService(client, TriageOptions(concurrency=config.concurrency))

    rows = list(service.triage(files))
    with ExitStack() as stack:
        sink = _open_sink(config.output_path, stdout, stack)
        CsvWriter(sink).write(rows)

    return EXIT_UNAVAILABLE if _every_create_failed(rows) else EXIT_OK


def _every_create_failed(rows: list[RowResult]) -> bool:
    return len(rows) > 0 and all(row.pedigree_id == "" for row in rows)


def _open_sink(path: Path | None, stdout: TextIO, stack: ExitStack) -> TextIO:
    if path is None:
        return stdout
    return stack.enter_context(path.open("w", encoding="utf-8", newline=""))


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
