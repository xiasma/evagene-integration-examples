"""Immutable configuration for the BayesMendel comparator CLI."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NoReturn, get_args

DEFAULT_BASE_URL = "https://evagene.net"

OutputFormat = Literal["table", "csv", "json"]
SUPPORTED_FORMATS: tuple[OutputFormat, ...] = get_args(OutputFormat)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    pedigree_id: str
    counselee_id: str | None
    output_format: OutputFormat


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    _require_uuid(args.pedigree_id, "pedigree-id")
    if args.counselee_id is not None:
        _require_uuid(args.counselee_id, "--counselee")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(
        base_url=base_url,
        api_key=api_key,
        pedigree_id=args.pedigree_id,
        counselee_id=args.counselee_id,
        output_format=args.output_format,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="bayesmendel-comparator",
        description="Compare BRCAPRO / MMRpro / PancPRO for one pedigree.",
    )
    parser.add_argument("pedigree_id", help="UUID of the pedigree to analyse.")
    parser.add_argument(
        "--counselee",
        dest="counselee_id",
        help="UUID of the target individual; defaults to the pedigree proband.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=SUPPORTED_FORMATS,
        default="table",
        help="Output format (default: table).",
    )
    return parser.parse_args(argv)


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")
