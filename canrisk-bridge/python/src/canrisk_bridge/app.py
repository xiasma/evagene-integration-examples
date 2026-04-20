"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from typing import TextIO

from .canrisk_client import ApiError, CanRiskClient, CanRiskFormatError
from .config import Config, ConfigError, load_config
from .http_gateway import HttpGateway, HttpxGateway
from .output_sink import OutputSink, WebBrowserLauncher

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_FORMAT = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway = HttpxGateway()
    try:
        return _bridge(config, gateway, stdout, stderr)
    finally:
        gateway.close()


def _bridge(
    config: Config,
    gateway: HttpGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    client = CanRiskClient(base_url=config.base_url, api_key=config.api_key, http=gateway)
    try:
        payload = client.fetch(config.pedigree_id)
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE
    except CanRiskFormatError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_FORMAT

    sink = OutputSink(output_dir=config.output_dir, browser=WebBrowserLauncher())
    saved_path = sink.save(pedigree_id=config.pedigree_id, payload=payload)
    stdout.write(f"{saved_path}\n")

    if config.open_browser:
        sink.open_upload_page()
    return EXIT_OK


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
