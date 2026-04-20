"""Immutable configuration for the Evagene MCP server."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://evagene.net"


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str


def load_config(env: Mapping[str, str]) -> Config:
    """Read the server's configuration from the environment.

    The MCP server is started by a client (Claude Desktop, Cursor, etc.)
    which injects the API key via ``env`` in the config stanza — there are
    no command-line arguments to parse.
    """
    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(base_url=base_url, api_key=api_key)
