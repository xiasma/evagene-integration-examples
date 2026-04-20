"""HTTP gateway abstraction and an ``httpx``-backed implementation.

The abstraction lets the test suite inject a fake; production code
receives :class:`HttpxGateway`.  Keeping the gateway narrow (one method)
avoids leaking transport concerns into the rest of the application.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class HttpGateway(Protocol):
    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by an ``httpx.Client``."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

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
