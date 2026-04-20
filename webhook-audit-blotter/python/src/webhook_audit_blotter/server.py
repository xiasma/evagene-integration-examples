"""Flask surface: three routes, no business logic."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from flask import Flask, Response, request

from .webhook_handler import IncomingDelivery, OutcomeStatus, WebhookHandler, WebhookOutcome

if TYPE_CHECKING:
    from .event_store import EventRow, EventStore

_DEFAULT_PAGE_SIZE = 100
_MAX_PAGE_SIZE = 1000


def build_app(*, handler: WebhookHandler, store: EventStore) -> Flask:
    app = Flask("webhook_audit_blotter")

    @app.post("/webhook")
    def webhook() -> Response:
        outcome = handler.handle(
            IncomingDelivery(
                raw_body=request.get_data(cache=False),
                signature_header=request.headers.get("X-Evagene-Signature-256"),
                event_type_header=request.headers.get("X-Evagene-Event"),
            ),
        )
        return _outcome_to_response(outcome)

    @app.get("/events")
    def list_events() -> Response:
        limit, offset = _parse_pagination()
        rows = store.list(limit, offset)
        body = "".join(json.dumps(_row_to_dict(row)) + "\n" for row in rows)
        return Response(body, status=200, mimetype="application/x-ndjson")

    @app.get("/events/verify")
    def verify_chain() -> Response:
        result = store.verify_chain()
        return Response(
            json.dumps({"ok": result.ok, "break_at": result.break_at}),
            status=200,
            mimetype="application/json",
        )

    return app


def _outcome_to_response(outcome: WebhookOutcome) -> Response:
    if outcome.status is OutcomeStatus.ACCEPTED:
        return Response(status=204)
    if outcome.status is OutcomeStatus.BAD_SIGNATURE:
        return Response("Invalid signature.", status=401, mimetype="text/plain")
    return Response(outcome.reason or "Bad request.", status=400, mimetype="text/plain")


def _row_to_dict(row: EventRow) -> dict[str, object]:
    return {
        "id": row.id,
        "receivedAt": row.received_at,
        "eventType": row.event_type,
        "body": row.body,
        "prevHash": row.prev_hash,
        "rowHash": row.row_hash,
    }


def _parse_pagination() -> tuple[int, int]:
    limit = _clamp(_read_int(request.args.get("limit"), _DEFAULT_PAGE_SIZE), 1, _MAX_PAGE_SIZE)
    offset = max(0, _read_int(request.args.get("offset"), 0))
    return limit, offset


def _read_int(raw: str | None, fallback: int) -> int:
    if raw is None:
        return fallback
    try:
        return int(raw)
    except ValueError:
        return fallback


def _clamp(value: int, lower: int, upper: int) -> int:
    return min(max(value, lower), upper)
