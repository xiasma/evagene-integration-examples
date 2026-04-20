"""Thin client for the subset of the Evagene REST API that the upgrader uses.

One method per endpoint; no orchestration (that lives in ``app``).  The
app layer talks to the :class:`EvageneApi` protocol so tests supply a
fake without a live HTTP layer.
"""

from __future__ import annotations

from typing import Any, Protocol

from .http_gateway import HttpGateway, HttpMethod

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class EvageneApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class EvageneApi(Protocol):
    def create_pedigree(self, display_name: str) -> str: ...

    def import_xeg_parse_only(self, pedigree_id: str, xeg_xml: str) -> dict[str, Any]: ...

    def import_xeg(self, pedigree_id: str, xeg_xml: str) -> None: ...

    def delete_pedigree(self, pedigree_id: str) -> None: ...


class EvageneClient:
    def __init__(self, *, base_url: str, api_key: str, http: HttpGateway) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    def create_pedigree(self, display_name: str) -> str:
        payload = self._request_json("POST", "/api/pedigrees", {"display_name": display_name})
        return _require_str(payload, "id")

    def import_xeg_parse_only(self, pedigree_id: str, xeg_xml: str) -> dict[str, Any]:
        path = f"/api/pedigrees/{pedigree_id}/import/xeg?mode=parse"
        return self._request_json("POST", path, {"content": xeg_xml})

    def import_xeg(self, pedigree_id: str, xeg_xml: str) -> None:
        path = f"/api/pedigrees/{pedigree_id}/import/xeg"
        self._send("POST", path, {"content": xeg_xml})

    def delete_pedigree(self, pedigree_id: str) -> None:
        self._send("DELETE", f"/api/pedigrees/{pedigree_id}", None)

    def _request_json(
        self, method: HttpMethod, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        response = self._send(method, path, body)
        try:
            payload = response.json()
        except ValueError as exc:
            raise EvageneApiError(
                f"Evagene API returned non-JSON body for {method} {path}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            kind = type(payload).__name__
            raise EvageneApiError(
                f"Evagene API returned non-object JSON for {method} {path}: {kind}"
            )
        return payload

    def _send(
        self, method: HttpMethod, path: str, body: dict[str, Any] | None
    ) -> Any:
        url = f"{self._base_url}{path}"
        response = self._http.send(method, url, headers=self._headers(), body=body)
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise EvageneApiError(
                f"Evagene API returned HTTP {response.status_code} for {method} {path}"
            )
        return response

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise EvageneApiError(f"Evagene response is missing string field {key!r}")
    return value
