"""HTTP gateway abstraction and an ``httpx``-backed implementation.

Keeping the gateway narrow (request + inspection) isolates transport
concerns so the Evagene client and the tool handlers can be tested with
a fake that records calls.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class HttpResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


class HttpGateway(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by ``httpx.AsyncClient``."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> HttpResponse:
        return await self._client.request(method, url, headers=headers, json=body)

    async def aclose(self) -> None:
        await self._client.aclose()
