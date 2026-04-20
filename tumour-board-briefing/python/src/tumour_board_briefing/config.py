"""Immutable configuration for the tumour-board-briefing CLI."""

from __future__ import annotations

import argparse
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import NoReturn

DEFAULT_BASE_URL = "https://evagene.net"

SUPPORTED_MODELS: tuple[str, ...] = (
    "CLAUS",
    "COUCH",
    "FRANK",
    "MANCHESTER",
    "NICE",
    "TYRER_CUZICK",
)

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
    counselee_id: str | None
    output_path: Path
    models: tuple[str, ...]


def load_config(
    argv: list[str],
    env: Mapping[str, str],
    *,
    today: date,
) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`.

    ``today`` is injected so the default output filename is deterministic
    in tests — the only non-pure concept in this module.
    """
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    _require_uuid(args.pedigree_id, "pedigree-id")
    if args.counselee_id is not None:
        _require_uuid(args.counselee_id, "--counselee")

    models = _parse_models(args.models)
    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    output_path = _resolve_output_path(args.output, args.pedigree_id, today)

    return Config(
        base_url=base_url,
        api_key=api_key,
        pedigree_id=args.pedigree_id,
        counselee_id=args.counselee_id,
        output_path=output_path,
        models=models,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="tumour-board-brief",
        description=(
            "Render a print-ready PDF briefing for an oncology MDT / tumour board "
            "from a single Evagene pedigree."
        ),
    )
    parser.add_argument("pedigree_id", help="UUID of the pedigree to brief.")
    parser.add_argument(
        "--counselee",
        dest="counselee_id",
        help="UUID of the target individual; defaults to the pedigree proband.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        help=(
            "Output PDF path. Defaults to "
            "./tumour-board-<short-uuid>-<yyyymmdd>.pdf in the current directory."
        ),
    )
    parser.add_argument(
        "--models",
        dest="models",
        default=",".join(SUPPORTED_MODELS).lower(),
        help=(
            "Comma-separated list of risk models. Default: "
            f"{','.join(m.lower() for m in SUPPORTED_MODELS)}."
        ),
    )
    return parser.parse_args(argv)


def _parse_models(raw: str) -> tuple[str, ...]:
    names = [part.strip().upper() for part in raw.split(",") if part.strip()]
    if not names:
        raise ConfigError("--models must name at least one model.")
    unknown = [name for name in names if name not in SUPPORTED_MODELS]
    if unknown:
        supported = ", ".join(m.lower() for m in SUPPORTED_MODELS)
        raise ConfigError(
            f"--models contains unsupported entries: {', '.join(unknown).lower()}. "
            f"Supported: {supported}."
        )
    # Preserve caller order while de-duplicating — model order drives the
    # layout of the risk summary table.
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return tuple(seen)


def _resolve_output_path(raw: str | None, pedigree_id: str, today: date) -> Path:
    if raw is not None:
        return Path(raw)
    short = uuid.UUID(pedigree_id).hex[:8]
    return Path(f"./tumour-board-{short}-{today.strftime('%Y%m%d')}.pdf")


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")
