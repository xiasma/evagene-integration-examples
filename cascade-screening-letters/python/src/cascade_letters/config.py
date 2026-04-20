"""Immutable configuration for the cascade-letters CLI."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"
DEFAULT_OUTPUT_DIR = "letters"

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
    output_dir: str
    template_id: str | None
    dry_run: bool


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    _require_uuid(args.pedigree_id, "pedigree-id")
    if args.template_id is not None:
        _require_uuid(args.template_id, "--template")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(
        base_url=base_url,
        api_key=api_key,
        pedigree_id=args.pedigree_id,
        output_dir=args.output_dir,
        template_id=args.template_id,
        dry_run=args.dry_run,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="cascade-letters",
        description="Draft cascade-screening letters for a pedigree's at-risk relatives.",
    )
    parser.add_argument("pedigree_id", help="UUID of the pedigree.")
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write letters into (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--template",
        dest="template_id",
        default=None,
        help="UUID of the analysis template; defaults to auto-discover or create one.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="List the relatives letters would be written for; do not call the run endpoint.",
    )
    return parser.parse_args(argv)


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")
