"""HMAC-SHA256 signature check for an Evagene webhook delivery.

The comparison uses :func:`hmac.compare_digest` to avoid leaking the
secret via wall-clock timing differences between a matching and a
mismatching byte.  Never compare signatures with ``==``.
"""

from __future__ import annotations

import hmac
from hashlib import sha256

_HEX_PREFIX = "sha256="
_SHA256_HEX_LENGTH = 64


def verify_signature(raw_body: bytes, signature_header: str | None, secret: str) -> bool:
    presented = _parse_signature_header(signature_header)
    if presented is None:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, sha256).digest()
    return hmac.compare_digest(presented, expected)


def _parse_signature_header(header: str | None) -> bytes | None:
    if header is None:
        return None
    stripped = header[len(_HEX_PREFIX) :] if header.startswith(_HEX_PREFIX) else header
    if len(stripped) != _SHA256_HEX_LENGTH:
        return None
    try:
        return bytes.fromhex(stripped)
    except ValueError:
        return None
