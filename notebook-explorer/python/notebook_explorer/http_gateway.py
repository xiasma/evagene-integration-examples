"""HTTP gateway abstraction and an ``httpx``-backed implementation.

The abstraction exists so tests can inject a fake that records requests
without needing the network.  The production gateway is a thin wrapper
around ``httpx.Client``; the notebook never sees it directly.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...

    @property
    def text(self) -> str: ...


class HttpGateway(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by an ``httpx.Client``."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return self._client.request(method, url, headers=headers, json=json_body)

    def close(self) -> None:
        self._client.close()
