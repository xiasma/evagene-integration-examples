"""Immutable configuration for the research-cohort-anonymiser CLI.

The CLI exposes four choices; :class:`Config` is the only shape the
rest of the pipeline ever reads.  Keeping the parsing and the value
object in one module means the contract is readable at a glance.
"""

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


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


class AgePrecision(str, Enum):
    YEAR = "year"
    FIVE_YEAR = "five-year"
    DECADE = "decade"


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    pedigree_id: str
    output_path: str | None
    as_new_pedigree: bool
    age_precision: AgePrecision
    keep_sex: bool


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    """Parse CLI arguments + environment into a validated :class:`Config`."""
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    _require_uuid(args.pedigree_id, "pedigree-id")

    if args.output_path is not None and args.as_new_pedigree:
        raise ConfigError("--output and --as-new-pedigree are mutually exclusive.")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(
        base_url=base_url,
        api_key=api_key,
        pedigree_id=args.pedigree_id,
        output_path=args.output_path,
        as_new_pedigree=args.as_new_pedigree,
        age_precision=AgePrecision(args.age_precision),
        keep_sex=args.keep_sex,
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="anonymise",
        description=(
            "Strip direct identifiers from an Evagene pedigree and emit a research-safe "
            "version to stdout, a file, or a new pedigree on the same account."
        ),
    )
    parser.add_argument("pedigree_id", help="UUID of the source pedigree.")
    parser.add_argument(
        "--output",
        dest="output_path",
        default=None,
        help="Write the anonymised JSON to this file instead of stdout.",
    )
    parser.add_argument(
        "--as-new-pedigree",
        dest="as_new_pedigree",
        action="store_true",
        help="Create a new pedigree on the account with anonymised content; print its ID.",
    )
    parser.add_argument(
        "--age-precision",
        dest="age_precision",
        choices=[option.value for option in AgePrecision],
        default=AgePrecision.YEAR.value,
        help="Granularity for dates and ages-at-event (default: year).",
    )
    parser.add_argument(
        "--keep-sex",
        dest="keep_sex",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Preserve biological_sex (default).  Pass --no-keep-sex to redact.",
    )
    return parser.parse_args(argv)


def _require_uuid(value: str, label: str) -> None:
    if not _UUID_RE.match(value):
        raise ConfigError(f"{label} must be a UUID, got: {value!r}")
