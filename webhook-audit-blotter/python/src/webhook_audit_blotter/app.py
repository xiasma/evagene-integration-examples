"""Composition root and runtime entry point."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

from .config import ConfigError, load_config
from .event_store import EventStore
from .server import build_app
from .webhook_handler import WebhookHandler


class _SystemClock:
    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def main() -> None:
    try:
        config = load_config(os.environ)
    except ConfigError as error:
        sys.stderr.write(f"error: {error}\n")
        sys.exit(64)

    store = EventStore(config.sqlite_path)
    handler = WebhookHandler(
        secret=config.webhook_secret,
        store=store,
        clock=_SystemClock(),
    )
    app = build_app(handler=handler, store=store)
    sys.stdout.write(
        f"Webhook audit blotter listening on http://localhost:{config.port}/\n",
    )
    sys.stdout.flush()
    app.run(host="0.0.0.0", port=config.port)
