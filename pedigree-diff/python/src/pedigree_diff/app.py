"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import TextIO

from .config import Config, ConfigError, OutputFormat, load_config
from .diff_engine import Diff, diff_pedigrees
from .evagene_client import ApiError, EvageneClient
from .formatters import FormatOptions, Formatter, JsonFormatter, MarkdownFormatter, TextFormatter
from .http_gateway import HttpGateway, HttpxGateway
from .snapshot import PedigreeSnapshot
from .snapshot_loader import SnapshotFileError, SnapshotLoader

EXIT_NO_CHANGES = 0
EXIT_CHANGES = 1
EXIT_USAGE = 64
EXIT_API = 69
EXIT_MALFORMED_SNAPSHOT = 70

_FORMATTERS: dict[OutputFormat, Formatter] = {
    OutputFormat.TEXT: TextFormatter(),
    OutputFormat.JSON: JsonFormatter(),
    OutputFormat.MARKDOWN: MarkdownFormatter(),
}


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway: HttpxGateway | None = None
    if config.api_key is not None:
        gateway = HttpxGateway()
    try:
        return _compare(config, gateway, stdout, stderr)
    finally:
        if gateway is not None:
            gateway.close()


def _compare(
    config: Config,
    gateway: HttpGateway | None,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    loader = _build_loader(config, gateway)
    try:
        before = loader.load(config.left)
        after = loader.load(config.right)
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_API
    except SnapshotFileError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_MALFORMED_SNAPSHOT

    diff = diff_pedigrees(before, after)
    _render(diff, before, after, config, stdout)
    return EXIT_CHANGES if diff.has_changes() else EXIT_NO_CHANGES


def _build_loader(config: Config, gateway: HttpGateway | None) -> SnapshotLoader:
    if gateway is None or config.api_key is None:
        return SnapshotLoader(fetcher=None)
    client = EvageneClient(
        base_url=config.base_url,
        api_key=config.api_key,
        http=gateway,
    )
    return SnapshotLoader(fetcher=client)


def _render(
    diff: Diff,
    before: PedigreeSnapshot,
    after: PedigreeSnapshot,
    config: Config,
    stdout: TextIO,
) -> None:
    options = FormatOptions(
        include_unchanged=config.include_unchanged,
        since=config.since,
        use_colour=_stdout_is_tty(stdout) and config.output_format is OutputFormat.TEXT,
        today=date.today(),
    )
    _FORMATTERS[config.output_format].render(diff, before, after, options, stdout)


def _stdout_is_tty(stdout: TextIO) -> bool:
    isatty = getattr(stdout, "isatty", None)
    return bool(isatty and isatty())


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
