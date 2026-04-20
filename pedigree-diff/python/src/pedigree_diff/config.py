"""Immutable configuration for the pedigree-diff CLI."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class SnapshotSource:
    """Where to load a pedigree snapshot from.

    Exactly one of :attr:`pedigree_id` or :attr:`path` is populated.
    """

    raw: str
    pedigree_id: str | None
    path: str | None


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str | None
    left: SnapshotSource
    right: SnapshotSource
    output_format: OutputFormat
    include_unchanged: bool
    since: datetime | None


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    left = _classify_source(args.left)
    right = _classify_source(args.right)

    api_key = (env.get("EVAGENE_API_KEY") or "").strip() or None
    if (left.pedigree_id or right.pedigree_id) and not api_key:
        raise ConfigError(
            "EVAGENE_API_KEY is required when either operand is a pedigree UUID.",
        )

    base_url = (env.get("EVAGENE_BASE_URL") or "").strip() or DEFAULT_BASE_URL
    return Config(
        base_url=base_url,
        api_key=api_key,
        left=left,
        right=right,
        output_format=OutputFormat(args.format),
        include_unchanged=bool(args.include_unchanged),
        since=_parse_since(args.since),
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="pedigree-diff",
        description=(
            "Compare two pedigrees (or two snapshots of the same pedigree) and "
            "produce a human-readable change log."
        ),
    )
    parser.add_argument(
        "left",
        help="Pedigree UUID or path to a snapshot JSON file (the 'before' side).",
    )
    parser.add_argument(
        "right",
        help="Pedigree UUID or path to a snapshot JSON file (the 'after' side).",
    )
    parser.add_argument(
        "--format",
        choices=[fmt.value for fmt in OutputFormat],
        default=OutputFormat.TEXT.value,
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--include-unchanged",
        action="store_true",
        help="Also list individuals with no changes.",
    )
    parser.add_argument(
        "--since",
        metavar="ISO",
        help="Only include events dated at or after this ISO-8601 timestamp.",
    )
    return parser.parse_args(argv)


def _classify_source(raw: str) -> SnapshotSource:
    if _UUID_RE.match(raw):
        return SnapshotSource(raw=raw, pedigree_id=raw, path=None)
    return SnapshotSource(raw=raw, pedigree_id=None, path=raw)


def _parse_since(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ConfigError(
            f"--since must be an ISO-8601 timestamp or date; got {raw!r}.",
        ) from exc
