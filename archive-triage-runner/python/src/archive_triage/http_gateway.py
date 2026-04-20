"""HTTP gateway abstraction and an ``httpx``-backed implementation.

Keeping the gateway narrow (one method across POST / GET / DELETE) lets
the tests inject a fake without leaking transport concerns into the
evagene client.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

import httpx

HttpMethod = Literal["GET", "POST", "DELETE"]


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class HttpGateway(Protocol):
    def send(
        self,
        method: HttpMethod,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by an ``httpx.Client``.

    Translates ``httpx.RequestError`` (DNS failure, connection refused,
    read timeout) into :class:`OSError` so callers can catch a single
    transport-layer exception type without depending on ``httpx``.
    """

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def send(
        self,
        method: HttpMethod,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            return self._client.request(method, url, headers=headers, json=body)
        except httpx.RequestError as error:
            raise OSError(f"HTTP transport error: {error}") from error

    def close(self) -> None:
        self._client.close()
