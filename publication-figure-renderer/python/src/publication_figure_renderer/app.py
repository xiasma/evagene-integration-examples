"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import Any, TextIO

from .config import Config, ConfigError, load_config
from .evagene_client import ApiError, EvageneClient
from .http_gateway import HttpxGateway
from .label_mapper import build_label_mapping
from .output_writer import write_svg
from .svg_deidentifier import InvalidSvgError, deidentify_svg

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69
EXIT_INVALID_SVG = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    gateway = HttpxGateway()
    try:
        return _render(config, gateway, stdout, stderr)
    finally:
        gateway.close()


def _render(
    config: Config,
    gateway: HttpxGateway,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    client = EvageneClient(base_url=config.base_url, api_key=config.api_key, http=gateway)
    try:
        svg_text = client.fetch_pedigree_svg(config.pedigree_id)
        name_to_label = (
            _build_name_to_label(client, config) if config.deidentify else {}
        )
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE

    try:
        rendered = deidentify_svg(
            svg_text, name_to_label, width=config.width, height=config.height
        )
    except InvalidSvgError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_INVALID_SVG

    written = write_svg(rendered, config.output_path)
    stdout.write(f"Wrote {written}\n")
    return EXIT_OK


def _build_name_to_label(client: EvageneClient, config: Config) -> dict[str, str]:
    detail = client.fetch_pedigree_detail(config.pedigree_id)
    id_to_label = build_label_mapping(detail, config.label_style)
    return _name_to_label_mapping(detail.get("individuals", []), id_to_label)


def _name_to_label_mapping(
    individuals: Any,
    id_to_label: Mapping[str, str],
) -> dict[str, str]:
    # The SVG replaces <text> nodes by their current content, so the
    # mapping we hand the deidentifier must be keyed by the original
    # display name, not by the individual id.  Individuals with no
    # display name contribute nothing to swap against.
    if not isinstance(individuals, list):
        return {}
    out: dict[str, str] = {}
    for individual in individuals:
        if not isinstance(individual, dict):
            continue
        name = individual.get("display_name")
        if not isinstance(name, str) or not name:
            continue
        ind_id = individual.get("id")
        if not isinstance(ind_id, str):
            continue
        out[name] = id_to_label[ind_id]
    return out


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
