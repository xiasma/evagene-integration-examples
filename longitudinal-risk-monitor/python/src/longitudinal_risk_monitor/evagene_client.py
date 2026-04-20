"""Evagene REST endpoints the monitor relies on.

Two reads (``GET /api/pedigrees``, list summaries; ``POST
/api/pedigrees/{id}/risk/calculate`` with ``model=NICE``).  HTTP 429
responses trigger bounded exponential backoff with jitter — up to
:data:`_MAX_RETRIES` retries — before surfacing as :class:`ApiError`.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .http_gateway import GetGateway, HttpResponse, PostGateway

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300
_HTTP_TOO_MANY = 429
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 0.5
_BACKOFF_JITTER_SECONDS = 0.25

Sleeper = Callable[[float], None]


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


@dataclass(frozen=True)
class PedigreeSummary:
    pedigree_id: str
    display_name: str


class EvageneClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        http_get: GetGateway,
        http_post: PostGateway,
        sleep: Sleeper,
        rng: random.Random | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http_get = http_get
        self._http_post = http_post
        self._sleep = sleep
        self._rng = rng or random.Random()

    def list_pedigrees(self) -> list[PedigreeSummary]:
        url = f"{self._base_url}/api/pedigrees"
        response = self._retrying(lambda: self._http_get.get_json(url, headers=self._headers()))
        payload = _require_2xx_json(response, url)
        if not isinstance(payload, list):
            raise ApiError(f"Expected a JSON array from {url}, got {type(payload).__name__}.")
        return [_to_summary(item) for item in payload]

    def calculate_nice(self, pedigree_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}/risk/calculate"
        body: dict[str, Any] = {"model": "NICE"}
        response = self._retrying(
            lambda: self._http_post.post_json(url, headers=self._headers(), body=body),
        )
        payload = _require_2xx_json(response, url)
        if not isinstance(payload, dict):
            raise ApiError(f"Expected a JSON object from {url}, got {type(payload).__name__}.")
        return payload

    def _retrying(self, call: Callable[[], HttpResponse]) -> HttpResponse:
        for attempt in range(_MAX_RETRIES + 1):
            response = call()
            if response.status_code != _HTTP_TOO_MANY or attempt == _MAX_RETRIES:
                return response
            self._sleep(self._backoff_seconds(attempt))
        raise AssertionError("unreachable")

    def _backoff_seconds(self, attempt: int) -> float:
        jitter: float = self._rng.random() * _BACKOFF_JITTER_SECONDS
        base: float = _BASE_BACKOFF_SECONDS * float(2**attempt)
        return base + jitter

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


def _require_2xx_json(response: HttpResponse, url: str) -> Any:
    if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
        raise ApiError(f"Evagene API returned HTTP {response.status_code} for {url}.")
    return response.json()


def _to_summary(item: Any) -> PedigreeSummary:
    if not isinstance(item, dict):
        raise ApiError(f"Expected pedigree objects in list response, got {type(item).__name__}.")
    pedigree_id = item.get("id")
    if not isinstance(pedigree_id, str):
        raise ApiError("Pedigree list entry is missing a string 'id'.")
    display_name = item.get("display_name")
    return PedigreeSummary(
        pedigree_id=pedigree_id,
        display_name=display_name if isinstance(display_name, str) else "",
    )
