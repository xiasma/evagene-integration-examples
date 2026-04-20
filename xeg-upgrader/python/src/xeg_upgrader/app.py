"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from pathlib import PurePath
from typing import TextIO

from .config import Config, ConfigError, RunMode, load_config
from .evagene_client import EvageneApi, EvageneApiError, EvageneClient
from .http_gateway import HttpGateway, HttpxGateway
from .summary_printer import render, summarise
from .xeg_reader import InvalidXegError, XegDocument, read_from_file

EXIT_SUCCESS = 0
EXIT_USAGE = 64
EXIT_API = 69
EXIT_INVALID_XEG = 70


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    try:
        xeg = read_from_file(config.input_path)
    except InvalidXegError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_INVALID_XEG

    gateway = HttpxGateway()
    try:
        return _execute(config, xeg, _build_client(config, gateway), stdout, stderr)
    finally:
        gateway.close()


def _build_client(config: Config, gateway: HttpGateway) -> EvageneApi:
    return EvageneClient(base_url=config.base_url, api_key=config.api_key, http=gateway)


def _execute(
    config: Config,
    xeg: XegDocument,
    api: EvageneApi,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    if config.mode is RunMode.PREVIEW:
        return _preview(config, xeg, api, stdout, stderr)
    return _create(config, xeg, api, stdout, stderr)


def _preview(
    config: Config,
    xeg: XegDocument,
    api: EvageneApi,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    scratch_id: str | None = None
    try:
        scratch_id = api.create_pedigree(f"xeg-upgrader preview ({config.display_name})")
        parsed = api.import_xeg_parse_only(scratch_id, xeg.raw_text)
        summary = summarise(parsed, PurePath(config.input_path).name)
        stdout.write(render(summary, RunMode.PREVIEW))
        return EXIT_SUCCESS
    except EvageneApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_API
    finally:
        if scratch_id is not None:
            _cleanup_scratch(api, scratch_id, stderr)


def _create(
    config: Config,
    xeg: XegDocument,
    api: EvageneApi,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        pedigree_id = api.create_pedigree(config.display_name)
        parsed = api.import_xeg_parse_only(pedigree_id, xeg.raw_text)
        api.import_xeg(pedigree_id, xeg.raw_text)
    except EvageneApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_API

    summary = summarise(parsed, PurePath(config.input_path).name)
    stdout.write(render(summary, RunMode.CREATE))
    stdout.write("\n")
    stdout.write(f"Pedigree created: {pedigree_id}\n")
    stdout.write(f"URL: {_pedigree_url(config.base_url, pedigree_id)}\n")
    return EXIT_SUCCESS


def _cleanup_scratch(api: EvageneApi, pedigree_id: str, stderr: TextIO) -> None:
    try:
        api.delete_pedigree(pedigree_id)
    except EvageneApiError as error:
        stderr.write(
            f"warning: failed to delete scratch pedigree {pedigree_id}: {error}\n"
        )


def _pedigree_url(base_url: str, pedigree_id: str) -> str:
    return f"{base_url.rstrip('/')}/pedigrees/{pedigree_id}"


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
