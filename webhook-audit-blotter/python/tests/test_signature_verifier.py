import hmac
from hashlib import sha256

from webhook_audit_blotter.signature_verifier import verify_signature

_SECRET = "shared-secret"
_BODY = b'{"event":"pedigree.updated"}'


def _valid_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()


def test_accepts_a_correctly_signed_body() -> None:
    assert verify_signature(_BODY, _valid_signature(_BODY, _SECRET), _SECRET)


def test_accepts_the_sha256_prefixed_form_evagene_actually_emits() -> None:
    assert verify_signature(_BODY, f"sha256={_valid_signature(_BODY, _SECRET)}", _SECRET)


def test_rejects_a_signature_that_does_not_match_the_body() -> None:
    tampered = b'{"event":"pedigree.deleted"}'
    assert not verify_signature(tampered, _valid_signature(_BODY, _SECRET), _SECRET)


def test_rejects_a_signature_computed_under_a_different_secret() -> None:
    assert not verify_signature(_BODY, _valid_signature(_BODY, "other-secret"), _SECRET)


def test_rejects_when_no_signature_header_is_present() -> None:
    assert not verify_signature(_BODY, None, _SECRET)


def test_rejects_non_hex_signature_header() -> None:
    header = "sha256=" + "nothex!!" + ("x" * 56)
    assert not verify_signature(_BODY, header, _SECRET)


def test_rejects_signature_of_wrong_length() -> None:
    assert not verify_signature(_BODY, "sha256=deadbeef", _SECRET)
