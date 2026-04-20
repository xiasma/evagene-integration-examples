"""Immutable configuration for the couple-carrier-risk CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NoReturn, get_args

DEFAULT_BASE_URL = "https://evagene.net"
AUTO_ANCESTRY = "auto"

OutputFormat = Literal["table", "csv", "json"]
SUPPORTED_FORMATS: tuple[OutputFormat, ...] = get_args(OutputFormat)


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    partner_a_file: str
    partner_b_file: str
    ancestry_a: str
    ancestry_b: str
    output_format: OutputFormat
    cleanup: bool


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "EVAGENE_API_KEY environment variable is required. "
            "Create a key at https://evagene.net (Account settings -> API keys).",
        )

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(
        base_url=base_url,
        api_key=api_key,
        partner_a_file=args.partner_a,
        partner_b_file=args.partner_b,
        ancestry_a=args.ancestry_a,
        ancestry_b=args.ancestry_b,
        output_format=args.output_format,
        cleanup=args.cleanup,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="couple-carrier-risk",
        description="Couple carrier screening from two 23andMe raw genotype files.",
    )
    parser.add_argument(
        "--partner-a",
        dest="partner_a",
        required=True,
        help="Path to partner A's 23andMe raw genotype TSV.",
    )
    parser.add_argument(
        "--partner-b",
        dest="partner_b",
        required=True,
        help="Path to partner B's 23andMe raw genotype TSV.",
    )
    parser.add_argument(
        "--ancestry-a",
        dest="ancestry_a",
        default=AUTO_ANCESTRY,
        help=(
            "Population key for partner A (e.g. ashkenazi_jewish, mediterranean, "
            "general). Default: auto (use ancestry recorded on the individual)."
        ),
    )
    parser.add_argument(
        "--ancestry-b",
        dest="ancestry_b",
        default=AUTO_ANCESTRY,
        help="Population key for partner B. Default: auto.",
    )
    parser.add_argument(
        "--output",
        dest="output_format",
        choices=SUPPORTED_FORMATS,
        default="table",
        help="Output format (default: table).",
    )
    cleanup = parser.add_mutually_exclusive_group()
    cleanup.add_argument(
        "--cleanup",
        dest="cleanup",
        action="store_true",
        default=True,
        help="Delete scratch pedigree and individuals after the run (default).",
    )
    cleanup.add_argument(
        "--no-cleanup",
        dest="cleanup",
        action="store_false",
        help="Keep the scratch pedigree so you can inspect it in the Evagene UI.",
    )
    return parser.parse_args(argv)
