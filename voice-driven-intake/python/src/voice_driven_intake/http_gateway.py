"""HTTP gateway abstraction and an ``httpx``-backed implementation."""

from __future__ import annotations

from typing import Any, Literal, Protocol

import httpx

HttpMethod = Literal["POST", "PATCH", "DELETE"]


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
        body: dict[str, Any] | None,
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by ``httpx.Client``."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def send(
        self,
        method: HttpMethod,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None,
    ) -> httpx.Response:
        return self._client.request(method, url, headers=headers, json=body)

    def close(self) -> None:
        self._client.close()
