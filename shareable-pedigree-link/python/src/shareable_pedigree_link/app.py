"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import TextIO

from .clock import Clock, SystemClock
from .config import Config, ConfigError, load_config
from .evagene_client import ApiError, CreateApiKeyRequest, EvageneClient
from .http_gateway import HttpGateway, HttpxGateway
from .key_name import build_key_name
from .presenter import present
from .snippet_builder import SnippetRequest, build_snippet

EXIT_OK = 0
EXIT_USAGE = 64
EXIT_UNAVAILABLE = 69

_RATE_PER_MINUTE = 60
_RATE_PER_DAY = 1000


@dataclass(frozen=True)
class Dependencies:
    gateway: HttpGateway
    clock: Clock


def run(
    argv: list[str],
    stdout: TextIO,
    stderr: TextIO,
    deps: Dependencies | None = None,
) -> int:
    try:
        config = load_config(argv, os.environ)
    except ConfigError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_USAGE

    resolved = deps or _default_dependencies()
    try:
        return _share(config, resolved, stdout, stderr)
    finally:
        _close_if_owned(resolved, deps)


def _share(
    config: Config,
    deps: Dependencies,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    client = EvageneClient(
        base_url=config.base_url,
        api_key=config.api_key,
        http=deps.gateway,
    )
    suffix = config.name_suffix or str(deps.clock.now_epoch_seconds())
    request = CreateApiKeyRequest(
        name=build_key_name(config.pedigree_id, suffix),
        rate_per_minute=_RATE_PER_MINUTE,
        rate_per_day=_RATE_PER_DAY,
    )
    try:
        minted = client.create_read_only_api_key(request)
    except ApiError as error:
        stderr.write(f"error: {error}\n")
        return EXIT_UNAVAILABLE

    snippet = build_snippet(
        SnippetRequest(
            embed_url=client.build_embed_url(config.pedigree_id, minted.plaintext_key),
            label=config.label,
            minted_at=deps.clock.now_iso(),
            plaintext_key=minted.plaintext_key,
            revoke_url=f"{config.base_url.rstrip('/')}/account/api-keys",
        ),
    )
    present(snippet, stdout)
    return EXIT_OK


def _default_dependencies() -> Dependencies:
    return Dependencies(gateway=HttpxGateway(), clock=SystemClock())


def _close_if_owned(resolved: Dependencies, injected: Dependencies | None) -> None:
    if injected is None and isinstance(resolved.gateway, HttpxGateway):
        resolved.gateway.close()


def main() -> None:
    sys.exit(run(sys.argv[1:], sys.stdout, sys.stderr))
