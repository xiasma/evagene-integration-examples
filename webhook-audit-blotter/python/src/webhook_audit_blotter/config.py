"""Immutable configuration for the audit-blotter server."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_PORT = 4000
DEFAULT_SQLITE_PATH = "./blotter.db"
_MAX_PORT = 65_535


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    port: int
    webhook_secret: str
    sqlite_path: str


def load_config(env: Mapping[str, str]) -> Config:
    secret = env.get("EVAGENE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise ConfigError("EVAGENE_WEBHOOK_SECRET environment variable is required.")
    return Config(
        port=_parse_port(env.get("PORT")),
        webhook_secret=secret,
        sqlite_path=env.get("SQLITE_PATH", "").strip() or DEFAULT_SQLITE_PATH,
    )


def _parse_port(raw: str | None) -> int:
    if raw is None or not raw.strip():
        return DEFAULT_PORT
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"PORT must be an integer between 1 and {_MAX_PORT}; got {raw!r}.",
        ) from exc
    if not 1 <= parsed <= _MAX_PORT:
        raise ConfigError(f"PORT must be an integer between 1 and {_MAX_PORT}; got {raw!r}.")
    return parsed
