"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from typing import TextIO

from .config import Config, ConfigError, load_config
from .couple_risk_calculator import ResponseSchemaError
from .evagene_client import ApiError, EvageneClient
from .genome_file import GenomeFileError
from .http_gateway import HttpxGateway
from .orchestrator import AncestryNotFoundError, run_couple_screening

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_SCHEMA = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway = HttpxGateway()
    try:
        client = EvageneClient(
            base_url=config.base_url, api_key=config.api_key, http=gateway,
        )
        return _screen(config, client, stdout, stderr)
    finally:
        gateway.close()


def _screen(config: Config, client: EvageneClient, stdout: TextIO, stderr: TextIO) -> int:
    try:
        run_couple_screening(config, client, stdout)
        return EXIT_OK
    except GenomeFileError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE
    except AncestryNotFoundError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE
    except ResponseSchemaError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_SCHEMA


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
