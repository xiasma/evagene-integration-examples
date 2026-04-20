"""End-to-end server test using Flask's built-in test client."""

import hmac
import json
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from webhook_audit_blotter.event_store import EventStore
from webhook_audit_blotter.server import build_app
from webhook_audit_blotter.webhook_handler import WebhookHandler

_SECRET = "integration-secret"
_FIXED_NOW = "2026-04-20T09:15:22Z"


class _FixedClock:
    def now_iso(self) -> str:
        return _FIXED_NOW


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[FlaskClient]:
    store = EventStore(str(tmp_path / "test.db"))
    handler = WebhookHandler(secret=_SECRET, store=store, clock=_FixedClock())
    app = build_app(handler=handler, store=store)
    app.config.update(TESTING=True)
    try:
        with app.test_client() as test_client:
            yield test_client
    finally:
        store.close()


def _sign(body: bytes) -> str:
    return f"sha256={hmac.new(_SECRET.encode('utf-8'), body, sha256).hexdigest()}"


def test_round_trip_signed_post_then_list_then_verify(client: FlaskClient) -> None:
    body = b'{"event":"pedigree.updated","pedigree_id":"abc"}'

    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Evagene-Event": "pedigree.updated",
            "X-Evagene-Signature-256": _sign(body),
        },
    )
    assert response.status_code == 204

    listed = client.get("/events")
    assert listed.status_code == 200
    lines = [line for line in listed.get_data(as_text=True).strip().split("\n") if line]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["eventType"] == "pedigree.updated"
    assert row["body"] == body.decode("utf-8")

    verify_response = client.get("/events/verify")
    assert verify_response.status_code == 200
    verdict = json.loads(verify_response.get_data(as_text=True))
    assert verdict == {"ok": True, "break_at": None}


def test_wrong_signature_returns_401_and_nothing_stored(client: FlaskClient) -> None:
    body = b'{"event":"pedigree.updated"}'

    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Evagene-Event": "pedigree.updated",
            "X-Evagene-Signature-256": "sha256=" + "a" * 64,
        },
    )
    assert response.status_code == 401

    listed = client.get("/events")
    assert listed.get_data(as_text=True).strip() == ""


def test_non_json_body_but_valid_signature_returns_400(client: FlaskClient) -> None:
    body = b"not-json"

    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Evagene-Event": "pedigree.updated",
            "X-Evagene-Signature-256": _sign(body),
        },
    )
    assert response.status_code == 400
