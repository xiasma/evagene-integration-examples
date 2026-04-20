"""Immutable configuration for the risk-monitor CLI.

CLI + environment are parsed into one of three dataclasses depending on
which subcommand was requested: :class:`RunConfig`, :class:`HistoryConfig`,
or :class:`SeedConfig`.  Nothing downstream branches on raw strings.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"
DEFAULT_SQLITE_PATH = "./risk-monitor.db"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


class Channel(str, Enum):
    STDOUT = "stdout"
    FILE = "file"
    SLACK_WEBHOOK = "slack-webhook"


class HistoryFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


@dataclass(frozen=True)
class ApiCredentials:
    base_url: str
    api_key: str


@dataclass(frozen=True)
class RunConfig:
    credentials: ApiCredentials
    sqlite_path: str
    channel: Channel
    channel_arg: str | None
    since: str | None
    dry_run: bool


@dataclass(frozen=True)
class HistoryConfig:
    sqlite_path: str
    pedigree_id: str | None
    format: HistoryFormat


@dataclass(frozen=True)
class SeedConfig:
    credentials: ApiCredentials
    sqlite_path: str


Config = RunConfig | HistoryConfig | SeedConfig


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    args = _parse_args(argv)
    sqlite_path = env.get("RISK_MONITOR_DB", "").strip() or DEFAULT_SQLITE_PATH

    if args.command == "run":
        return _build_run_config(args, env, sqlite_path)
    if args.command == "history":
        return _build_history_config(args, sqlite_path)
    if args.command == "seed":
        return SeedConfig(credentials=_require_credentials(env), sqlite_path=sqlite_path)
    raise ConfigError(f"Unknown subcommand: {args.command!r}")


def _build_run_config(args: argparse.Namespace, env: Mapping[str, str], db: str) -> RunConfig:
    channel = _parse_channel(args.channel)
    if channel is Channel.FILE and not args.channel_arg:
        raise ConfigError("--channel file requires --channel-arg <path>.")
    if channel is Channel.SLACK_WEBHOOK and not args.channel_arg:
        raise ConfigError("--channel slack-webhook requires --channel-arg <url>.")
    return RunConfig(
        credentials=_require_credentials(env),
        sqlite_path=db,
        channel=channel,
        channel_arg=args.channel_arg,
        since=args.since,
        dry_run=bool(args.dry_run),
    )


def _build_history_config(args: argparse.Namespace, db: str) -> HistoryConfig:
    if args.pedigree is not None:
        _require_uuid(args.pedigree, "--pedigree")
    return HistoryConfig(
        sqlite_path=db,
        pedigree_id=args.pedigree,
        format=_parse_format(args.format),
    )


def _require_credentials(env: Mapping[str, str]) -> ApiCredentials:
    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")
    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return ApiCredentials(base_url=base_url, api_key=api_key)


def _parse_channel(raw: str) -> Channel:
    try:
        return Channel(raw)
    except ValueError as exc:
        valid = ", ".join(c.value for c in Channel)
        raise ConfigError(f"--channel must be one of {valid}; got {raw!r}.") from exc


def _parse_format(raw: str) -> HistoryFormat:
    try:
        return HistoryFormat(raw)
    except ValueError as exc:
        valid = ", ".join(f.value for f in HistoryFormat)
        raise ConfigError(f"--format must be one of {valid}; got {raw!r}.") from exc


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="risk-monitor",
        description="Detect NICE-category changes across your Evagene pedigrees on a schedule.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Recompute NICE for every pedigree, notify on change.")
    run.add_argument("--since", help="Unused bookkeeping; echoed into the summary for audit.")
    run.add_argument(
        "--channel",
        default=Channel.STDOUT.value,
        help="Where to emit change notifications (stdout|file|slack-webhook).",
    )
    run.add_argument("--channel-arg", dest="channel_arg", help="Channel-specific argument.")
    run.add_argument("--dry-run", dest="dry_run", action="store_true")

    history = subparsers.add_parser("history", help="List recorded category-change events.")
    history.add_argument("--pedigree", help="Filter to one pedigree UUID.")
    history.add_argument("--format", default=HistoryFormat.TEXT.value, help="text|json")

    subparsers.add_parser("seed", help="Populate baseline from current state; emit no events.")

    return parser.parse_args(argv)
