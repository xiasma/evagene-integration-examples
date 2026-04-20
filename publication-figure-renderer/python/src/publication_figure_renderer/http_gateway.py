"""HTTP gateway abstraction and an ``httpx``-backed implementation.

The abstraction lets the test suite inject a fake; production code
receives :class:`HttpxGateway`.  One method is all we need -- this demo
only reads from Evagene, it never writes.
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
    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> HttpResponse: ...


class HttpxGateway:
    """Concrete :class:`HttpGateway` backed by an ``httpx.Client``."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
    ) -> HttpResponse:
        return self._client.get(url, headers=headers)

    def close(self) -> None:
        self._client.close()
