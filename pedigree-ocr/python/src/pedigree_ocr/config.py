"""Immutable configuration for the pedigree-ocr CLI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .vision_extractor import DEFAULT_MODEL

DEFAULT_BASE_URL = "https://evagene.net"


class ConfigError(ValueError):
    """Raised when CLI or environment configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    image_path: Path | None
    commit: bool
    show_prompt: bool
    model: str
    anthropic_api_key: str | None
    evagene_api_key: str | None
    evagene_base_url: str


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    args = _parse_args(argv)
    model = args.model or DEFAULT_MODEL

    if args.show_prompt:
        return Config(
            image_path=_as_path(args.image_file),
            commit=False,
            show_prompt=True,
            model=model,
            anthropic_api_key=None,
            evagene_api_key=None,
            evagene_base_url=_resolve_base_url(env),
        )

    image_path = _as_path(args.image_file)
    if image_path is None:
        raise ConfigError("An image file is required (PNG, JPG, or PDF).")

    anthropic_api_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_api_key:
        raise ConfigError("ANTHROPIC_API_KEY environment variable is required.")

    evagene_api_key: str | None = None
    if args.commit:
        evagene_api_key = env.get("EVAGENE_API_KEY", "").strip() or None
        if evagene_api_key is None:
            raise ConfigError(
                "--commit requires the EVAGENE_API_KEY environment variable to be set."
            )

    return Config(
        image_path=image_path,
        commit=args.commit,
        show_prompt=False,
        model=model,
        anthropic_api_key=anthropic_api_key,
        evagene_api_key=evagene_api_key,
        evagene_base_url=_resolve_base_url(env),
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="pedigree-ocr",
        description="Extract a family pedigree from a photograph or scan via Claude Vision, "
        "and optionally create the pedigree in Evagene.",
    )
    parser.add_argument(
        "image_file",
        nargs="?",
        default=None,
        help="Path to the pedigree image (.png, .jpg, .jpeg, or .pdf).",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="After extraction, create the pedigree in Evagene.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Override the Claude vision model (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the system prompt and tool schema that would be sent to Anthropic, then exit.",
    )
    return parser.parse_args(argv)


def _as_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _resolve_base_url(env: Mapping[str, str]) -> str:
    return env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
