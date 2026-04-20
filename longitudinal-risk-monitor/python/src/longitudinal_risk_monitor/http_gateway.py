"""HTTP gateway abstractions plus an ``httpx``-backed implementation.

Two gateways are defined so that the Evagene client and the Slack
notifier depend only on what they need (interface segregation):
:class:`GetGateway` for ``GET``, :class:`PostGateway` for ``POST``.
The concrete :class:`HttpxGateway` satisfies both.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class GetGateway(Protocol):
    def get_json(self, url: str, *, headers: dict[str, str]) -> HttpResponse: ...


class PostGateway(Protocol):
    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete gateway satisfying both :class:`GetGateway` and :class:`PostGateway`."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def get_json(self, url: str, *, headers: dict[str, str]) -> httpx.Response:
        return self._client.get(url, headers=headers)

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> httpx.Response:
        return self._client.post(url, headers=headers, json=body)

    def close(self) -> None:
        self._client.close()
