"""Thin client for the subset of the Evagene REST API used by this demo.

One method per endpoint; no orchestration (that lives in
:class:`TriageService`).  Depends on an :class:`HttpGateway` so tests can
supply a fake.
"""

from __future__ import annotations

from typing import Any, Protocol

from .http_gateway import HttpGateway, HttpMethod

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class EvageneApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class EvageneApi(Protocol):
    """The surface :class:`TriageService` depends on."""

    def create_pedigree(self, display_name: str) -> str: ...

    def import_gedcom(self, pedigree_id: str, gedcom_text: str) -> None: ...

    def has_proband(self, pedigree_id: str) -> bool: ...

    def calculate_nice(self, pedigree_id: str) -> dict[str, Any]: ...

    def delete_pedigree(self, pedigree_id: str) -> None: ...


class EvageneClient:
    def __init__(self, *, base_url: str, api_key: str, http: HttpGateway) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    def create_pedigree(self, display_name: str) -> str:
        payload = self._request_object("POST", "/api/pedigrees", {"display_name": display_name})
        return _require_str(payload, "id")

    def import_gedcom(self, pedigree_id: str, gedcom_text: str) -> None:
        # NOTE: Evagene's GEDCOM import takes a JSON body with a "content"
        # field, not raw text/plain — see https://evagene.net/docs.
        self._request(
            "POST",
            f"/api/pedigrees/{pedigree_id}/import/gedcom",
            body={"content": gedcom_text},
        )

    def has_proband(self, pedigree_id: str) -> bool:
        payload = self._request_object("GET", f"/api/pedigrees/{pedigree_id}", body=None)
        individuals = payload.get("individuals")
        if not isinstance(individuals, list):
            return False
        return any(_is_proband(member) for member in individuals)

    def calculate_nice(self, pedigree_id: str) -> dict[str, Any]:
        return self._request_object(
            "POST",
            f"/api/pedigrees/{pedigree_id}/risk/calculate",
            body={"model": "NICE"},
        )

    def delete_pedigree(self, pedigree_id: str) -> None:
        self._request("DELETE", f"/api/pedigrees/{pedigree_id}", body=None)

    def _request_object(
        self,
        method: HttpMethod,
        path: str,
        body: dict[str, Any] | None,
    ) -> dict[str, Any]:
        response = self._request(method, path, body=body)
        payload = response.json()
        if not isinstance(payload, dict):
            kind = type(payload).__name__
            raise EvageneApiError(
                f"Evagene API returned non-object JSON for {method} {path}: {kind}"
            )
        return payload

    def _request(
        self,
        method: HttpMethod,
        path: str,
        *,
        body: dict[str, Any] | None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            response = self._http.send(method, url, headers=self._headers(), body=body)
        except OSError as error:
            raise EvageneApiError(
                f"Evagene API unreachable for {method} {path}: {error}"
            ) from error
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


def _is_proband(member: Any) -> bool:
    if not isinstance(member, dict):
        return False
    value = member.get("proband")
    return isinstance(value, int | float) and value > 0


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise EvageneApiError(f"Evagene response is missing string field {key!r}")
    return value
