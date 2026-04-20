"""Typed Evagene API client for the three endpoints the briefing needs.

One class, three methods:
- ``fetch_pedigree_detail`` — ``GET /api/pedigrees/{id}``
- ``fetch_pedigree_svg``    — ``GET /api/pedigrees/{id}/export.svg``
- ``calculate_risk``        — ``POST /api/pedigrees/{id}/risk/calculate``

Each method maps transport failures onto :class:`ApiError`; schema
interpretation is the aggregator's job, not the client's.
"""

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

    def fetch_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}"
        response = self._http.get(url, headers=self._json_headers())
        self._require_2xx(response, url)
        payload = response.json()
        if not isinstance(payload, dict):
            raise ApiError(
                f"Pedigree detail endpoint returned non-object JSON: {type(payload).__name__}"
            )
        return payload

    def fetch_pedigree_svg(self, pedigree_id: str) -> bytes:
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}/export.svg"
        response = self._http.get(url, headers=self._svg_headers())
        self._require_2xx(response, url)
        return response.content

    def calculate_risk(
        self,
        pedigree_id: str,
        model: str,
        *,
        counselee_id: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}/risk/calculate"
        body: dict[str, Any] = {"model": model}
        if counselee_id is not None:
            body["counselee_id"] = counselee_id

        response = self._http.post_json(url, headers=self._json_headers(), body=body)
        self._require_2xx(response, f"{url} (model={model})")
        payload = response.json()
        if not isinstance(payload, dict):
            raise ApiError(
                f"Risk endpoint returned non-object JSON for model {model}: "
                f"{type(payload).__name__}"
            )
        return payload

    def _require_2xx(self, response: Any, context: str) -> None:
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise ApiError(f"Evagene API returned HTTP {response.status_code} for {context}")

    def _json_headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _svg_headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Accept": "image/svg+xml",
        }
