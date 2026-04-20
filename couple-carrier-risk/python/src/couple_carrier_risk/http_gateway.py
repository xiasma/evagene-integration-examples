"""HTTP gateway abstraction and an ``httpx``-backed implementation.

Every verb the Evagene client needs (POST, GET, DELETE) goes through the
same narrow seam, so tests can substitute a fake without monkey-patching
the transport.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class HttpResponse(Protocol):
    status_code: int

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


class HttpGateway(Protocol):
    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> HttpResponse: ...

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> HttpResponse: ...

    def delete(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by an ``httpx.Client``."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> HttpResponse:
        return self._client.post(url, headers=headers, json=body, params=params)

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> HttpResponse:
        return self._client.get(url, headers=headers)

    def delete(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> HttpResponse:
        return self._client.delete(url, headers=headers)

    def close(self) -> None:
        self._client.close()
