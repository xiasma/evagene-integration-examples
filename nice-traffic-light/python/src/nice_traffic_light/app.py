"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from typing import TextIO

from .classifier import ResponseSchemaError, classify_nice_response
from .config import Config, ConfigError, load_config
from .http_gateway import HttpGateway, HttpxGateway
from .presenter import present
from .risk_api_client import ApiError, RiskApiClient
from .traffic_light import TrafficLight, to_traffic_light

EXIT_GREEN = 0
EXIT_AMBER = 1
EXIT_RED = 2
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
        return _classify(config, gateway, stdout, stderr)
    finally:
        gateway.close()


def _classify(
    config: Config,
    gateway: HttpGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    client = RiskApiClient(base_url=config.base_url, api_key=config.api_key, http=gateway)
    try:
        payload = client.calculate_nice(
            config.pedigree_id,
            counselee_id=config.counselee_id,
        )
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE

    try:
        outcome = classify_nice_response(payload)
    except ResponseSchemaError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_SCHEMA

    report = to_traffic_light(outcome)
    present(report, stdout)
    return _exit_code_for(report.colour)


def _exit_code_for(colour: TrafficLight) -> int:
    return {
        TrafficLight.GREEN: EXIT_GREEN,
        TrafficLight.AMBER: EXIT_AMBER,
        TrafficLight.RED: EXIT_RED,
    }[colour]


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
