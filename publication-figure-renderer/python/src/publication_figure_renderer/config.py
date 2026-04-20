"""Immutable configuration for the publication-figure-renderer CLI."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class LabelStyle(str, Enum):
    INITIALS = "initials"
    GENERATION_NUMBER = "generation-number"
    OFF = "off"


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    pedigree_id: str
    output_path: str
    deidentify: bool
    label_style: LabelStyle
    width: int | None
    height: int | None


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
        output_path=args.output,
        deidentify=args.deidentify,
        label_style=LabelStyle(args.label_style),
        width=args.width,
        height=args.height,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="pubfig",
        description="Render an Evagene pedigree as a publication-quality SVG.",
    )
    parser.add_argument("pedigree_id", help="UUID of the pedigree to render.")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the SVG file to.",
    )
    parser.add_argument(
        "--deidentify",
        action="store_true",
        help="Replace display names according to --label-style.",
    )
    parser.add_argument(
        "--label-style",
        choices=[style.value for style in LabelStyle],
        default=LabelStyle.GENERATION_NUMBER.value,
        help="How to label individuals when --deidentify is set.",
    )
    parser.add_argument(
        "--width",
        type=_positive_int,
        default=None,
        help="Override the root SVG width (pixels).",
    )
    parser.add_argument(
        "--height",
        type=_positive_int,
        default=None,
        help="Override the root SVG height (pixels).",
    )
    return parser.parse_args(argv)


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"must be a positive integer, got: {raw!r}"
        ) from exc
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got: {raw!r}")
    return value


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")
