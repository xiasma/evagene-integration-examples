"""Composition root -- wires concretes to abstractions and starts the server."""

from __future__ import annotations

import os
import sys

from .config import Config, ConfigError, load_config
from .evagene_client import EvageneClient
from .http_gateway import HttpxGateway
from .intake_service import IntakeService
from .server import build_flask_app


def run(config: Config) -> None:
    gateway = HttpxGateway()
    try:
        client = EvageneClient(
            base_url=config.base_url,
            api_key=config.api_key,
            http=gateway,
        )
        service = IntakeService(client)
        app = build_flask_app(service=service, evagene_base_url=config.base_url)
        sys.stdout.write(
            f"Family-history intake form listening on http://localhost:{config.port}/\n"
        )
        sys.stdout.flush()
        app.run(host="127.0.0.1", port=config.port, debug=False, use_reloader=False)
    finally:
        gateway.close()


def main() -> None:
    try:
        config = load_config(os.environ)
    except ConfigError as error:
        sys.stderr.write(f"error: {error}\n")
        sys.exit(64)
    run(config)
