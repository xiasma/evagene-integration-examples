"""Thin client for the two Evagene endpoints this demo needs."""

from __future__ import annotations

from typing import Any

from .http_gateway import HttpGateway

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class EvageneClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        http: HttpGateway,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    def fetch_pedigree_svg(self, pedigree_id: str) -> str:
        """Return the raw SVG document for a pedigree."""
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}/export.svg"
        response = self._http.get(
            url, headers=self._headers(accept="image/svg+xml")
        )
        self._require_ok(response, url)
        return response.text

    def fetch_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]:
        """Return the pedigree detail (metadata + resolved individuals)."""
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}"
        response = self._http.get(
            url, headers=self._headers(accept="application/json")
        )
        self._require_ok(response, url)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError(f"Evagene API returned invalid JSON for {url}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ApiError(
                f"Evagene API returned non-object JSON for {url}: "
                f"{type(payload).__name__}"
            )
        return payload

    def _headers(self, *, accept: str) -> dict[str, str]:
        return {"X-API-Key": self._api_key, "Accept": accept}

    @staticmethod
    def _require_ok(response: Any, url: str) -> None:
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise ApiError(f"Evagene API returned HTTP {response.status_code} for {url}")
