import hmac
from hashlib import sha256

from webhook_audit_blotter.event_store import AppendArgs
from webhook_audit_blotter.webhook_handler import (
    IncomingDelivery,
    OutcomeStatus,
    WebhookHandler,
)

_SECRET = "shared-secret"
_FIXED_NOW = "2026-04-20T09:15:22Z"
_EVENT = "pedigree.updated"


class _RecordingStore:
    def __init__(self) -> None:
        self.appended: list[AppendArgs] = []

    def append(self, args: AppendArgs) -> int:
        self.appended.append(args)
        return len(self.appended)


class _FixedClock:
    def now_iso(self) -> str:
        return _FIXED_NOW


def _sign(body: bytes, secret: str = _SECRET) -> str:
    return f"sha256={hmac.new(secret.encode('utf-8'), body, sha256).hexdigest()}"


def _handler(store: _RecordingStore) -> WebhookHandler:
    return WebhookHandler(secret=_SECRET, store=store, clock=_FixedClock())


def _delivery(
    body: bytes,
    *,
    signature: str | None,
    event_type: str | None = _EVENT,
) -> IncomingDelivery:
    return IncomingDelivery(
        raw_body=body,
        signature_header=signature,
        event_type_header=event_type,
    )


def test_valid_signature_and_json_body_appends_and_returns_accepted() -> None:
    body = b'{"event":"pedigree.updated"}'
    store = _RecordingStore()

    outcome = _handler(store).handle(_delivery(body, signature=_sign(body)))

    assert outcome.status is OutcomeStatus.ACCEPTED
    assert len(store.appended) == 1
    assert store.appended[0] == AppendArgs(_FIXED_NOW, _EVENT, body.decode("utf-8"))


def test_bad_signature_returns_bad_signature_and_does_not_append() -> None:
    body = b'{"event":"pedigree.updated"}'
    store = _RecordingStore()

    outcome = _handler(store).handle(_delivery(body, signature=_sign(body, "wrong")))

    assert outcome.status is OutcomeStatus.BAD_SIGNATURE
    assert store.appended == []


def test_missing_signature_header_rejected_as_bad_signature() -> None:
    body = b'{"event":"pedigree.updated"}'
    store = _RecordingStore()

    outcome = _handler(store).handle(_delivery(body, signature=None))

    assert outcome.status is OutcomeStatus.BAD_SIGNATURE


def test_non_json_body_bad_request_nothing_stored() -> None:
    body = b"not-json"
    store = _RecordingStore()

    outcome = _handler(store).handle(_delivery(body, signature=_sign(body)))

    assert outcome.status is OutcomeStatus.BAD_REQUEST
    assert store.appended == []


def test_json_array_also_rejected_as_bad_request() -> None:
    body = b"[1,2,3]"
    store = _RecordingStore()

    outcome = _handler(store).handle(_delivery(body, signature=_sign(body)))

    assert outcome.status is OutcomeStatus.BAD_REQUEST


def test_missing_event_header_rejected_as_bad_request() -> None:
    body = b'{"ok":true}'
    store = _RecordingStore()

    outcome = _handler(store).handle(_delivery(body, signature=_sign(body), event_type=None))

    assert outcome.status is OutcomeStatus.BAD_REQUEST
