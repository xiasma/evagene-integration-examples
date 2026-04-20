"""Thin async client for the Evagene REST endpoints the MCP tools need.

One method per endpoint.  Each method shapes the URL, delegates the
transport to :class:`HttpGateway`, and raises :class:`ApiError` on any
non-2xx response.  No parsing, no domain logic — that belongs in the
tool handlers.
"""

from __future__ import annotations

from typing import Any

from .http_gateway import HttpGateway

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class EvageneClient:
    def __init__(self, *, base_url: str, api_key: str, http: HttpGateway) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    async def list_pedigrees(self) -> list[dict[str, Any]]:
        payload = await self._get_json("/api/pedigrees")
        if not isinstance(payload, list):
            raise ApiError(
                f"Expected a JSON array from /api/pedigrees, "
                f"got {type(payload).__name__}"
            )
        return payload

    async def get_pedigree(self, pedigree_id: str) -> dict[str, Any]:
        return await self._get_object(f"/api/pedigrees/{pedigree_id}")

    async def describe_pedigree(self, pedigree_id: str) -> str:
        return await self._get_text(f"/api/pedigrees/{pedigree_id}/describe")

    async def list_risk_models(self, pedigree_id: str) -> dict[str, Any]:
        return await self._get_object(f"/api/pedigrees/{pedigree_id}/risk/models")

    async def calculate_risk(
        self,
        pedigree_id: str,
        *,
        model: str,
        counselee_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"model": model}
        if counselee_id is not None:
            body["counselee_id"] = counselee_id
        return await self._post_object(
            f"/api/pedigrees/{pedigree_id}/risk/calculate",
            body=body,
        )

    async def create_individual(
        self,
        *,
        display_name: str,
        biological_sex: str,
    ) -> dict[str, Any]:
        return await self._post_object(
            "/api/individuals",
            body={"display_name": display_name, "biological_sex": biological_sex},
        )

    async def add_individual_to_pedigree(
        self,
        pedigree_id: str,
        individual_id: str,
    ) -> dict[str, Any]:
        return await self._post_object(
            f"/api/pedigrees/{pedigree_id}/individuals/{individual_id}",
            body={},
        )

    async def add_relative(
        self,
        pedigree_id: str,
        *,
        relative_of: str,
        relative_type: str,
        display_name: str = "",
        biological_sex: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "relative_of": relative_of,
            "relative_type": relative_type,
            "display_name": display_name,
        }
        if biological_sex is not None:
            body["biological_sex"] = biological_sex
        return await self._post_object(
            f"/api/pedigrees/{pedigree_id}/register/add-relative",
            body=body,
        )

    # ------------------------------------------------------------------
    # Transport helpers
    # ------------------------------------------------------------------

    async def _get_json(self, path: str) -> Any:
        response = await self._http.request(
            "GET", self._url(path), headers=self._headers(),
        )
        self._raise_for_status(response, path)
        return response.json()

    async def _get_object(self, path: str) -> dict[str, Any]:
        payload = await self._get_json(path)
        return self._require_object(payload, path)

    async def _get_text(self, path: str) -> str:
        response = await self._http.request(
            "GET", self._url(path), headers=self._headers(),
        )
        self._raise_for_status(response, path)
        return response.text

    async def _post_object(self, path: str, *, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._http.request(
            "POST", self._url(path), headers=self._headers(), body=body,
        )
        self._raise_for_status(response, path)
        return self._require_object(response.json(), path)

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _raise_for_status(response: Any, path: str) -> None:
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise ApiError(
                f"Evagene API returned HTTP {response.status_code} for {path}"
            )

    @staticmethod
    def _require_object(payload: Any, path: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ApiError(
                f"Expected JSON object from {path}, got {type(payload).__name__}"
            )
        return payload
