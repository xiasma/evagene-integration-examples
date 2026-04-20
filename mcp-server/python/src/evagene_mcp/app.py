"""Composition root and runtime entry point for ``python -m evagene_mcp``."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from mcp.server.stdio import stdio_server

from .config import ConfigError, load_config
from .evagene_client import EvageneClient
from .http_gateway import HttpxGateway
from .server import SERVER_NAME, build_server


def main() -> None:
    _configure_logging()
    try:
        config = load_config(os.environ)
    except ConfigError as error:
        sys.stderr.write(f"evagene-mcp: {error}\n")
        sys.exit(64)

    asyncio.run(_run(config.base_url, config.api_key))


async def _run(base_url: str, api_key: str) -> None:
    gateway = HttpxGateway()
    client = EvageneClient(base_url=base_url, api_key=api_key, http=gateway)
    server = build_server(client)

    try:
        async with stdio_server() as (read_stream, write_stream):
            init_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, init_options)
    finally:
        await gateway.aclose()


def _configure_logging() -> None:
    """Send every log record to stderr — stdout is the MCP transport."""
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(os.environ.get("EVAGENE_MCP_LOG_LEVEL", "INFO"))
    logging.getLogger(SERVER_NAME).setLevel(logging.INFO)
