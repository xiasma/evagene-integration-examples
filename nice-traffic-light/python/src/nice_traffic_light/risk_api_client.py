"""Call Evagene's ``risk/calculate`` endpoint for the NICE model."""

from __future__ import annotations

from typing import Any

from .http_gateway import HttpGateway

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class RiskApiClient:
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

    def calculate_nice(
        self,
        pedigree_id: str,
        *,
        counselee_id: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/api/pedigrees/{pedigree_id}/risk/calculate"
        body: dict[str, Any] = {"model": "NICE"}
        if counselee_id is not None:
            body["counselee_id"] = counselee_id

        response = self._http.post_json(url, headers=self._headers(), body=body)
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise ApiError(f"Evagene API returned HTTP {response.status_code} for {url}")

        payload = response.json()
        if not isinstance(payload, dict):
            raise ApiError(f"Evagene API returned non-object JSON: {type(payload).__name__}")
        return payload

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
