"""Thin client for the subset of the Evagene REST API used when ``--commit`` is set.

One method per endpoint, no orchestration (that lives in :class:`EvageneWriter`).
Mirrors the client used by sibling demos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .extracted_family import BiologicalSex
from .http_gateway import HttpGateway, HttpMethod

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class EvageneApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


@dataclass(frozen=True)
class CreateIndividualArgs:
    display_name: str
    biological_sex: BiologicalSex
    year_of_birth: int | None = None


@dataclass(frozen=True)
class AddRelativeArgs:
    pedigree_id: str
    relative_of: str
    relative_type: str
    display_name: str
    biological_sex: BiologicalSex
    year_of_birth: int | None = None


class EvageneApi(Protocol):
    def create_pedigree(self, display_name: str) -> str: ...

    def create_individual(self, args: CreateIndividualArgs) -> str: ...

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None: ...

    def designate_as_proband(self, individual_id: str) -> None: ...

    def add_relative(self, args: AddRelativeArgs) -> str: ...


class EvageneClient:
    def __init__(self, *, base_url: str, api_key: str, http: HttpGateway) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    def create_pedigree(self, display_name: str) -> str:
        payload = self._request("POST", "/api/pedigrees", {"display_name": display_name})
        return _require_str(payload, "id")

    def create_individual(self, args: CreateIndividualArgs) -> str:
        body: dict[str, Any] = {
            "display_name": args.display_name,
            "biological_sex": args.biological_sex.value,
        }
        _attach_year(body, args.year_of_birth)
        payload = self._request("POST", "/api/individuals", body)
        return _require_str(payload, "id")

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None:
        self._request_ignoring_body(
            "POST",
            f"/api/pedigrees/{pedigree_id}/individuals/{individual_id}",
            {},
        )

    def designate_as_proband(self, individual_id: str) -> None:
        self._request_ignoring_body(
            "PATCH", f"/api/individuals/{individual_id}", {"proband": 1}
        )

    def add_relative(self, args: AddRelativeArgs) -> str:
        body: dict[str, Any] = {
            "relative_of": args.relative_of,
            "relative_type": args.relative_type,
            "display_name": args.display_name,
            "biological_sex": args.biological_sex.value,
        }
        _attach_year(body, args.year_of_birth)
        payload = self._request(
            "POST",
            f"/api/pedigrees/{args.pedigree_id}/register/add-relative",
            body,
        )
        individual = _require_dict(payload, "individual")
        return _require_str(individual, "id")

    def _request(self, method: HttpMethod, path: str, body: dict[str, Any]) -> dict[str, Any]:
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

    def _request_ignoring_body(
        self, method: HttpMethod, path: str, body: dict[str, Any]
    ) -> None:
        """For endpoints whose success response carries no useful body."""
        self._send(method, path, body)

    def _send(self, method: HttpMethod, path: str, body: dict[str, Any]) -> Any:
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


def _attach_year(body: dict[str, Any], year: int | None) -> None:
    if year is not None:
        body["properties"] = {"year_of_birth": year}


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise EvageneApiError(f"Evagene response is missing string field {key!r}")
    return value


def _require_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise EvageneApiError(f"Evagene response is missing object field {key!r}")
    return value
