"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TextIO

from .cascade_service import (
    CascadeRequest,
    CascadeResult,
    CascadeService,
    NoAtRiskRelativesError,
)
from .config import Config, ConfigError, load_config
from .evagene_client import EvageneApiError, EvageneClient
from .http_gateway import HttpGateway, HttpxGateway
from .letter_writer import DiskLetterSink

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_EMPTY = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway = HttpxGateway()
    try:
        return _run_with_gateway(config, gateway, stdout, stderr)
    finally:
        gateway.close()


def _run_with_gateway(
    config: Config,
    gateway: HttpGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    service = CascadeService(
        client=EvageneClient(
            base_url=config.base_url,
            api_key=config.api_key,
            http=gateway,
        ),
        sink=DiskLetterSink(Path(config.output_dir)),
    )
    request = CascadeRequest(
        pedigree_id=config.pedigree_id,
        template_override=config.template_id,
        dry_run=config.dry_run,
    )
    try:
        result = service.generate_letters(request)
    except EvageneApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE
    except NoAtRiskRelativesError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_EMPTY

    _report(result, config.dry_run, stdout)
    return EXIT_OK


def _report(result: CascadeResult, dry_run: bool, stdout: TextIO) -> None:
    if dry_run:
        for target in result.targets:
            stdout.write(f"{target.display_name} ({target.relationship})\n")
        return
    for path in result.written_paths:
        stdout.write(f"{path}\n")


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
