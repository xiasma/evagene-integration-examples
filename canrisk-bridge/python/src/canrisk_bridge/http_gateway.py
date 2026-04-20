"""HTTP gateway abstraction and an ``httpx``-backed implementation.

The gateway returns the response body as text because the CanRisk endpoint
serves ``text/tab-separated-values`` rather than JSON.
"""

from __future__ import annotations

from typing import Protocol

import httpx


class HttpResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...


class HttpGateway(Protocol):
    def get_text(self, url: str, *, headers: dict[str, str]) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by an ``httpx.Client``."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def get_text(self, url: str, *, headers: dict[str, str]) -> HttpResponse:
        return self._client.get(url, headers=headers)

    def close(self) -> None:
        self._client.close()
