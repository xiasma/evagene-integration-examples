"""Immutable configuration for the xeg-upgrader CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePath
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


class RunMode(str, Enum):
    PREVIEW = "preview"
    CREATE = "create"


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    input_path: str
    mode: RunMode
    display_name: str


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL

    mode = RunMode.CREATE if args.create else RunMode.PREVIEW
    display_name = args.name if args.name is not None else _default_display_name(args.input_path)

    return Config(
        base_url=base_url,
        api_key=api_key,
        input_path=args.input_path,
        mode=mode,
        display_name=display_name,
    )


def _default_display_name(input_path: str) -> str:
    return PurePath(input_path).stem


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="xeg-upgrade",
        description=(
            "Validate or import a legacy Evagene v1 .xeg pedigree. "
            "Default behaviour is preview (parse only, no pedigree persisted)."
        ),
    )
    parser.add_argument("input_path", help="Path to the .xeg file to process.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--preview",
        action="store_true",
        help="Parse only — do not create any pedigree (default).",
    )
    mode.add_argument(
        "--create",
        action="store_true",
        help="Create a new pedigree and import the .xeg into it.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Override the pedigree display name (defaults to the file stem).",
    )
    return parser.parse_args(argv)
