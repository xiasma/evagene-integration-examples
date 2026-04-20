"""Immutable configuration for the intake-form server."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://evagene.net"
DEFAULT_PORT = 3000
_MIN_PORT = 1
_MAX_PORT = 65535


class ConfigError(ValueError):
    """Raised when required configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    port: int


def load_config(env: Mapping[str, str]) -> Config:
    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    port = _parse_port(env.get("PORT", "").strip())
    return Config(base_url=base_url, api_key=api_key, port=port)


def _parse_port(raw: str) -> int:
    if not raw:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"PORT must be an integer between {_MIN_PORT} and {_MAX_PORT}; got {raw!r}."
        ) from exc
    if not _MIN_PORT <= port <= _MAX_PORT:
        raise ConfigError(
            f"PORT must be an integer between {_MIN_PORT} and {_MAX_PORT}; got {port}."
        )
    return port
