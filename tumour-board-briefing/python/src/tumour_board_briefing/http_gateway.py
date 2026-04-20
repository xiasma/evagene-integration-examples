"""HTTP gateway abstraction and an ``httpx``-backed implementation.

The tumour-board briefing fetches three kinds of resource (pedigree JSON,
pedigree SVG, risk JSON), so the gateway exposes both ``get`` and
``post_json`` operations. Keeping the abstraction narrow lets tests
inject a fake that records every call.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class HttpResponse(Protocol):
    """Minimum contract we need from an HTTP response.

    Attributes are declared as read-only properties to match the
    ``httpx.Response`` surface (``.content`` and ``.text`` are computed
    properties there, not writable fields).
    """

    status_code: int

    @property
    def content(self) -> bytes: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


class HttpGateway(Protocol):
    def get(self, url: str, *, headers: dict[str, str]) -> HttpResponse: ...

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by an ``httpx.Client``.

    Return types are declared as the :class:`HttpResponse` protocol
    rather than the concrete ``httpx.Response`` to keep the gateway
    substitutable at call sites that only know about the abstraction.
    """

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def get(self, url: str, *, headers: dict[str, str]) -> HttpResponse:
        return self._client.get(url, headers=headers)

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResponse:
        return self._client.post(url, headers=headers, json=body)

    def close(self) -> None:
        self._client.close()
