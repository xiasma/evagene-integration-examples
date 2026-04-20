"""Immutable CLI + environment configuration."""

from __future__ import annotations

import argparse
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .inheritance import Mode
from .puzzle_blueprint import Generations, Size

DEFAULT_BASE_URL = "https://evagene.net"
DEFAULT_OUTPUT_DIR = Path("./puzzles")

_DEFAULT_DISEASE_BY_MODE: dict[Mode, str] = {
    Mode.AD: "Huntington's Disease",
    Mode.AR: "Cystic Fibrosis",
    Mode.XLR: "Haemophilia A",
    Mode.XLD: "Rett Syndrome",
    Mode.MT: "Leber Hereditary Optic Neuropathy",
}


class ConfigError(ValueError):
    """Configuration is missing or malformed."""


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    mode: Mode | None  # None means "pick randomly at run time"
    generations: Generations
    size: Size
    disease_name: str | None
    output_dir: Path
    cleanup: bool
    seed: int


def default_disease_for(mode: Mode) -> str:
    return _DEFAULT_DISEASE_BY_MODE[mode]


def load_config(argv: list[str], env: Mapping[str, str]) -> Config:
    args = _parse_args(argv)

    api_key = env.get("EVAGENE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("EVAGENE_API_KEY environment variable is required.")

    base_url = env.get("EVAGENE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return Config(
        base_url=base_url,
        api_key=api_key,
        mode=_parse_mode(args.mode),
        generations=_parse_generations(args.generations),
        size=_parse_size(args.size),
        disease_name=_parse_disease_name(args.disease),
        output_dir=Path(args.output_dir),
        cleanup=not args.no_cleanup,
        seed=args.seed if args.seed is not None else secrets.randbits(63),
    )


class _NonExitingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = _NonExitingParser(
        prog="puzzle-generator",
        description="Generate a random pedigree puzzle for teaching Mendelian inheritance.",
    )
    parser.add_argument(
        "--mode",
        default="random",
        help="AD | AR | XLR | XLD | MT | random (default: random).",
    )
    parser.add_argument(
        "--generations",
        default="3",
        help="Number of generations to generate: 3 or 4 (default: 3).",
    )
    parser.add_argument(
        "--size",
        default="medium",
        help="small | medium | large (offspring per couple; default: medium).",
    )
    parser.add_argument(
        "--disease",
        default=None,
        help="Disease display name to use; defaults to the curated choice for the mode.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for the generated question/answer files (default: ./puzzles).",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Leave the scratch pedigree on the Evagene account after generation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Integer seed for the PRNG; omit for a fresh random puzzle.",
    )
    return parser.parse_args(argv)


def _parse_mode(raw: str) -> Mode | None:
    normalised = raw.strip().upper()
    if normalised == "RANDOM":
        return None
    try:
        return Mode(normalised)
    except ValueError as exc:
        valid = ", ".join(m.value for m in Mode)
        raise ConfigError(f"--mode must be one of {valid} or 'random'; got {raw!r}") from exc


def _parse_generations(raw: str) -> Generations:
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"--generations must be 3 or 4; got {raw!r}") from exc
    try:
        return Generations(value)
    except ValueError as exc:
        raise ConfigError(f"--generations must be 3 or 4; got {value}") from exc


def _parse_size(raw: str) -> Size:
    try:
        return Size(raw.strip().lower())
    except ValueError as exc:
        valid = ", ".join(s.value for s in Size)
        raise ConfigError(f"--size must be one of {valid}; got {raw!r}") from exc


def _parse_disease_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed:
        raise ConfigError("--disease must not be empty.")
    return trimmed
