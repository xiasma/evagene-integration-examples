"""Immutable configuration for the CanRisk bridge CLI."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"

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
    output_dir: Path
    open_browser: bool


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
        output_dir=Path(args.output_dir) if args.output_dir else Path.cwd(),
        open_browser=bool(args.open_browser),
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="canrisk-bridge",
        description="Export an Evagene pedigree as a ##CanRisk 2.0 file.",
    )
    parser.add_argument("pedigree_id", help="UUID of the pedigree to export.")
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        help="Directory to save the file into; defaults to the current working directory.",
    )
    parser.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        help="Open https://canrisk.org in the default browser after saving.",
    )
    return parser.parse_args(argv)


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")
