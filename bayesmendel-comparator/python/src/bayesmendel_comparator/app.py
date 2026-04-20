"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from typing import Any, TextIO

from .comparison_builder import ResponseSchemaError, build_comparison
from .config import Config, ConfigError, load_config
from .http_gateway import HttpGateway, HttpxGateway
from .model_registry import BAYESMENDEL_MODELS
from .presenter import presenter_for
from .risk_api_client import ApiError, RiskApiClient

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_SCHEMA = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway = HttpxGateway()
    try:
        return _compare(config, gateway, stdout, stderr)
    finally:
        gateway.close()


def _compare(
    config: Config,
    gateway: HttpGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    client = RiskApiClient(base_url=config.base_url, api_key=config.api_key, http=gateway)

    try:
        payloads = _fetch_all_models(client, config)
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE

    try:
        comparison = build_comparison(payloads)
    except ResponseSchemaError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_SCHEMA

    presenter_for(config.output_format)(comparison, stdout)
    return EXIT_OK


def _fetch_all_models(client: RiskApiClient, config: Config) -> dict[str, dict[str, Any]]:
    return {
        model: client.calculate(
            config.pedigree_id,
            model,
            counselee_id=config.counselee_id,
        )
        for model in BAYESMENDEL_MODELS
    }


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
