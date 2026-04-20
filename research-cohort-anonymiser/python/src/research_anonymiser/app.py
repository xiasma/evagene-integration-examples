"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TextIO

from .anonymiser import AnonymisationRules, anonymise
from .config import Config, ConfigError, load_config
from .evagene_client import EvageneApi, EvageneApiError, EvageneClient
from .generation_assigner import assign_generation_labels
from .http_gateway import HttpxGateway
from .k_anonymity_estimator import estimate_k_anonymity
from .presenter import render_json
from .writer import FileSink, NewPedigreeSink, OutputSink, StdoutSink

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
        client = EvageneClient(
            base_url=config.base_url,
            api_key=config.api_key,
            http=gateway,
        )
        return _anonymise(config, client, stdout, stderr)
    finally:
        gateway.close()


def _anonymise(
    config: Config,
    client: EvageneApi,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        source = client.get_pedigree_detail(config.pedigree_id)
    except EvageneApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE

    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=config.age_precision, keep_sex=config.keep_sex)
    anonymised = anonymise(source, labels, rules)
    estimate = estimate_k_anonymity(anonymised)
    rendered = render_json(anonymised, estimate)

    sink = _sink_for(config, client, stdout, stderr)
    try:
        sink.emit(rendered, anonymised)
    except EvageneApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE
    return EXIT_OK


def _sink_for(
    config: Config,
    client: EvageneApi,
    stdout: TextIO,
    stderr: TextIO,
) -> OutputSink:
    if config.as_new_pedigree:
        return NewPedigreeSink(client, stdout)
    if config.output_path is not None:
        return FileSink(Path(config.output_path), stderr)
    return StdoutSink(stdout)


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
