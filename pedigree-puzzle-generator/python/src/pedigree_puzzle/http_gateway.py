"""HTTP gateway abstraction and an ``httpx``-backed implementation.

The abstraction is deliberately narrow (one ``send``).  Tests inject a
fake; production code receives :class:`HttpxGateway`, which also
handles HTTP 429 rate-limit responses by honouring the server's
``Retry-After`` header (a few retries, bounded wait).  The puzzle
generator makes many writes in quick succession and would otherwise
hit the default per-minute rate limit on an interactive API key.
"""

from __future__ import annotations

import time
from typing import Any, Literal, Protocol

import httpx

HttpMethod = Literal["GET", "POST", "PATCH", "DELETE"]
_HTTP_TOO_MANY_REQUESTS = 429
_MAX_RETRIES = 4
_FALLBACK_RETRY_SECONDS = 2.0


class HttpResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


class HttpGateway(Protocol):
    def send(
        self,
        method: HttpMethod,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> HttpResponse: ...


class Sleeper(Protocol):
    def __call__(self, seconds: float, /) -> None: ...


class HttpxGateway:
    def __init__(
        self,
        timeout_seconds: float = 15.0,
        *,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)
        self._sleep = sleeper or time.sleep

    def send(
        self,
        method: HttpMethod,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> HttpResponse:
        attempts = 0
        while True:
            response = self._client.request(
                method,
                url,
                headers=headers,
                json=body if body is not None else None,
                params=params,
            )
            if response.status_code != _HTTP_TOO_MANY_REQUESTS or attempts >= _MAX_RETRIES:
                return response
            self._sleep(_retry_after_seconds(response))
            attempts += 1

    def close(self) -> None:
        self._client.close()


def _retry_after_seconds(response: httpx.Response) -> float:
    raw = response.headers.get("Retry-After", "")
    if not raw.strip():
        return _FALLBACK_RETRY_SECONDS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _FALLBACK_RETRY_SECONDS
