"""Immutable configuration loaded from environment variables."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://evagene.net"


class ConfigError(ValueError):
    """Required configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str


def load_config(env: Mapping[str, str]) -> Config:
    """Build a :class:`Config` from the ``EVAGENE_*`` environment variables."""
    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "EVAGENE_API_KEY environment variable is required. "
            "See ../README.md for how to mint a key."
        )
    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(base_url=base_url.rstrip("/"), api_key=api_key)
