"""Immutable configuration for the shareable-pedigree-link CLI."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"
DEFAULT_LABEL = "Family pedigree"

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
    name_suffix: str | None
    label: str


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    _require_uuid(args.pedigree_id, "pedigree-id")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(
        base_url=base_url,
        api_key=api_key,
        pedigree_id=args.pedigree_id,
        name_suffix=args.name_suffix,
        label=args.label or DEFAULT_LABEL,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="shareable-pedigree-link",
        description="Mint a read-only Evagene API key and print an iframe embed snippet.",
    )
    parser.add_argument("pedigree_id", help="UUID of the pedigree to share.")
    parser.add_argument(
        "--name",
        dest="name_suffix",
        help="Suffix for the minted API key's name; defaults to a Unix timestamp.",
    )
    parser.add_argument(
        "--label",
        dest="label",
        help=f"Human-readable iframe title; defaults to '{DEFAULT_LABEL}'.",
    )
    return parser.parse_args(argv)


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")
