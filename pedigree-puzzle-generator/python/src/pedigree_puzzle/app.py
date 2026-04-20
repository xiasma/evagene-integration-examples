"""Composition root and CLI entry point."""

from __future__ import annotations

import logging
import os
import random
import sys
from datetime import UTC, datetime
from typing import TextIO

from .config import Config, ConfigError, default_disease_for, load_config
from .evagene_client import EvageneApiError, EvageneClient
from .http_gateway import HttpxGateway
from .inheritance import Mode
from .orchestrator import Clock, PuzzleOrchestrator
from .puzzle_blueprint import build_blueprint

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_SOFTWARE = 70


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    logger = _configure_logger(stderr)
    gateway = HttpxGateway()
    try:
        return _generate(config, gateway, stdout, stderr, logger, _SystemClock())
    finally:
        gateway.close()


def _generate(
    config: Config,
    gateway: HttpxGateway,
    stdout: TextIO,
    stderr: TextIO,
    logger: logging.Logger,
    clock: Clock,
) -> int:
    chosen_mode = config.mode if config.mode is not None else _random_mode(config.seed)
    disease_name = config.disease_name or default_disease_for(chosen_mode)
    blueprint = build_blueprint(
        mode=chosen_mode,
        generations=config.generations,
        size=config.size,
        seed=config.seed,
    )

    client = EvageneClient(base_url=config.base_url, api_key=config.api_key, http=gateway)
    orchestrator = PuzzleOrchestrator(
        client,
        clock=clock,
        evagene_base_url=config.base_url,
        logger=logger,
    )

    try:
        result = orchestrator.generate(
            blueprint=blueprint,
            disease_name=disease_name,
            output_dir=config.output_dir,
            cleanup=config.cleanup,
        )
    except EvageneApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE

    stdout.write(f"Wrote {result.artefact.question_path}\n")
    stdout.write(f"Wrote {result.artefact.answer_path}\n")
    stdout.write(
        f"Pedigree on Evagene: {config.base_url}/pedigrees/{result.pedigree_id}"
        + (" (deleted)" if result.pedigree_was_deleted else "")
        + "\n"
    )
    return EXIT_OK


def _random_mode(seed: int) -> Mode:
    choices = tuple(Mode)
    return random.Random(seed ^ 0xA5A5).choice(choices)


def _configure_logger(stderr: TextIO) -> logging.Logger:
    logger = logging.getLogger("pedigree_puzzle")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def main() -> None:
    try:
        sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
    except Exception as error:
        sys.stderr.write(f"error: {error}\n")
        sys.exit(EXIT_SOFTWARE)
