"""Immutable configuration for the archive-triage CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"
DEFAULT_CONCURRENCY = 4
_MAX_CONCURRENCY = 32


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    input_dir: Path
    output_path: Path | None
    concurrency: int


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    concurrency = _require_positive(args.concurrency, "--concurrency")

    return Config(
        base_url=base_url,
        api_key=api_key,
        input_dir=Path(args.input_dir),
        output_path=Path(args.output) if args.output is not None else None,
        concurrency=concurrency,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="archive-triage",
        description="Bulk-triage a folder of GEDCOM pedigrees against NICE CG164 / NG101.",
    )
    parser.add_argument("input_dir", help="Directory scanned recursively for *.ged files.")
    parser.add_argument(
        "--output",
        help="CSV file to write. Defaults to stdout when omitted.",
        default=None,
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=(
            f"Maximum pedigrees processed in parallel (default {DEFAULT_CONCURRENCY}, "
            f"max {_MAX_CONCURRENCY})."
        ),
    )
    return parser.parse_args(argv)


def _require_positive(value: int, label: str) -> int:
    if value < 1 or value > _MAX_CONCURRENCY:
        raise ConfigError(f"{label} must be between 1 and {_MAX_CONCURRENCY}, got {value}.")
    return value
