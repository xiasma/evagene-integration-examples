"""Framework-agnostic webhook orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .event_store import AppendArgs
from .signature_verifier import verify_signature


class OutcomeStatus(Enum):
    ACCEPTED = "accepted"
    BAD_SIGNATURE = "bad_signature"
    BAD_REQUEST = "bad_request"


@dataclass(frozen=True)
class WebhookOutcome:
    status: OutcomeStatus
    row_id: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class IncomingDelivery:
    raw_body: bytes
    signature_header: str | None
    event_type_header: str | None


class AppendOnlyStore(Protocol):
    def append(self, args: AppendArgs) -> int: ...


class Clock(Protocol):
    def now_iso(self) -> str: ...


class WebhookHandler:
    def __init__(self, *, secret: str, store: AppendOnlyStore, clock: Clock) -> None:
        self._secret = secret
        self._store = store
        self._clock = clock

    def handle(self, delivery: IncomingDelivery) -> WebhookOutcome:
        if not verify_signature(delivery.raw_body, delivery.signature_header, self._secret):
            return WebhookOutcome(status=OutcomeStatus.BAD_SIGNATURE)
        try:
            body_text = delivery.raw_body.decode("utf-8")
        except UnicodeDecodeError:
            return WebhookOutcome(status=OutcomeStatus.BAD_REQUEST, reason="Body is not UTF-8.")
        if not _is_json_object(body_text):
            return WebhookOutcome(
                status=OutcomeStatus.BAD_REQUEST,
                reason="Body is not a JSON object.",
            )
        event_type = (delivery.event_type_header or "").strip()
        if not event_type:
            return WebhookOutcome(
                status=OutcomeStatus.BAD_REQUEST,
                reason="Missing X-Evagene-Event header.",
            )
        row_id = self._store.append(
            AppendArgs(
                received_at=self._clock.now_iso(),
                event_type=event_type,
                body=body_text,
            ),
        )
        return WebhookOutcome(status=OutcomeStatus.ACCEPTED, row_id=row_id)


def _is_json_object(text: str) -> bool:
    try:
        parsed = json.loads(text)
    except ValueError:
        return False
    return isinstance(parsed, dict)
