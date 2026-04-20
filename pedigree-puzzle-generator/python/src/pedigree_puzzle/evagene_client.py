"""Thin client for the subset of the Evagene REST API used by the puzzle generator.

One method per endpoint; no orchestration.  The orchestrator composes
these calls.  The ``add_individual_to_pedigree`` / ``designate_as_proband``
methods deliberately tolerate empty response bodies -- Evagene returns
an empty body on those endpoints and httpx's ``.json()`` raises on an
empty string.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .http_gateway import HttpGateway, HttpMethod, HttpResponse
from .inheritance import Sex

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class EvageneApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class DiseaseNotFoundError(EvageneApiError):
    """The requested disease could not be resolved in the Evagene catalogue."""


@dataclass(frozen=True)
class DiseaseSummary:
    disease_id: str
    display_name: str


@dataclass(frozen=True)
class CreateIndividualArgs:
    display_name: str
    sex: Sex


@dataclass(frozen=True)
class AddRelativeArgs:
    pedigree_id: str
    relative_of: str
    relative_type: str
    display_name: str
    sex: Sex


class EvageneApi(Protocol):
    def search_diseases(self, name_fragment: str) -> DiseaseSummary: ...

    def create_pedigree(self, display_name: str) -> str: ...

    def create_individual(self, args: CreateIndividualArgs) -> str: ...

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None: ...

    def designate_as_proband(self, individual_id: str) -> None: ...

    def add_relative(self, args: AddRelativeArgs) -> str: ...

    def add_disease_to_individual(self, individual_id: str, disease_id: str) -> None: ...

    def get_pedigree_svg(self, pedigree_id: str) -> str: ...

    def delete_pedigree(self, pedigree_id: str) -> None: ...


class EvageneClient:
    def __init__(self, *, base_url: str, api_key: str, http: HttpGateway) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    def search_diseases(self, name_fragment: str) -> DiseaseSummary:
        """Return the disease whose display name best matches ``name_fragment``.

        Prefers an exact (case-insensitive) match, then a prefix match,
        then a substring match.  The REST endpoint has no server-side
        ``?search=`` parameter, so we list and filter client-side.
        """
        payload = self._request("GET", "/api/diseases")
        diseases = _require_list(payload, "diseases")
        needle = name_fragment.strip().lower()
        exact: DiseaseSummary | None = None
        prefix: DiseaseSummary | None = None
        substring: DiseaseSummary | None = None
        for raw in diseases:
            if not isinstance(raw, dict):
                continue
            name = raw.get("display_name")
            disease_id = raw.get("id")
            if not (isinstance(name, str) and isinstance(disease_id, str)):
                continue
            lowered = name.lower()
            if lowered == needle and exact is None:
                exact = DiseaseSummary(disease_id=disease_id, display_name=name)
            elif lowered.startswith(needle) and prefix is None:
                prefix = DiseaseSummary(disease_id=disease_id, display_name=name)
            elif needle in lowered and substring is None:
                substring = DiseaseSummary(disease_id=disease_id, display_name=name)
        match = exact or prefix or substring
        if match is None:
            raise DiseaseNotFoundError(
                f"No disease in the Evagene catalogue matched {name_fragment!r}."
            )
        return match

    def create_pedigree(self, display_name: str) -> str:
        payload = self._request("POST", "/api/pedigrees", body={"display_name": display_name})
        return _require_str_field(payload, "id")

    def create_individual(self, args: CreateIndividualArgs) -> str:
        body = {"display_name": args.display_name, "biological_sex": args.sex.value}
        payload = self._request("POST", "/api/individuals", body=body)
        return _require_str_field(payload, "id")

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None:
        self._send_ignoring_body(
            "POST",
            f"/api/pedigrees/{pedigree_id}/individuals/{individual_id}",
            body={},
        )

    def designate_as_proband(self, individual_id: str) -> None:
        self._send_ignoring_body(
            "PATCH", f"/api/individuals/{individual_id}", body={"proband": 1}
        )

    def add_relative(self, args: AddRelativeArgs) -> str:
        body = {
            "relative_of": args.relative_of,
            "relative_type": args.relative_type,
            "display_name": args.display_name,
            "biological_sex": args.sex.value,
        }
        payload = self._request(
            "POST",
            f"/api/pedigrees/{args.pedigree_id}/register/add-relative",
            body=body,
        )
        individual = _require_dict_field(payload, "individual")
        return _require_str_field(individual, "id")

    def add_disease_to_individual(self, individual_id: str, disease_id: str) -> None:
        # Default affection_status on the create body is "affected"
        # server-side, which is exactly what a puzzle generator wants.
        self._send_ignoring_body(
            "POST",
            f"/api/individuals/{individual_id}/diseases",
            body={"disease_id": disease_id},
        )

    def get_pedigree_svg(self, pedigree_id: str) -> str:
        response = self._dispatch("GET", f"/api/pedigrees/{pedigree_id}/export.svg")
        _assert_2xx(response, "GET", f"/api/pedigrees/{pedigree_id}/export.svg")
        return response.text

    def delete_pedigree(self, pedigree_id: str) -> None:
        self._send_ignoring_body("DELETE", f"/api/pedigrees/{pedigree_id}")

    def _request(
        self,
        method: HttpMethod,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> Any:
        response = self._dispatch(method, path, body=body)
        _assert_2xx(response, method, path)
        try:
            return response.json()
        except ValueError as exc:
            raise EvageneApiError(
                f"Evagene API returned non-JSON body for {method} {path}: {exc}"
            ) from exc

    def _send_ignoring_body(
        self,
        method: HttpMethod,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> None:
        response = self._dispatch(method, path, body=body)
        _assert_2xx(response, method, path)

    def _dispatch(
        self,
        method: HttpMethod,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> HttpResponse:
        url = f"{self._base_url}{path}"
        return self._http.send(method, url, headers=self._headers(), body=body)

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


def _assert_2xx(response: HttpResponse, method: str, path: str) -> None:
    if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
        raise EvageneApiError(
            f"Evagene API returned HTTP {response.status_code} for {method} {path}"
        )


def _require_str_field(payload: Any, key: str) -> str:
    if not isinstance(payload, dict):
        raise EvageneApiError(f"Evagene response is not an object, cannot read field {key!r}.")
    value = payload.get(key)
    if not isinstance(value, str):
        raise EvageneApiError(f"Evagene response is missing string field {key!r}.")
    return value


def _require_dict_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise EvageneApiError(f"Evagene response is missing object field {key!r}.")
    return value


def _require_list(payload: Any, label: str) -> list[Any]:
    if not isinstance(payload, list):
        raise EvageneApiError(f"Evagene response for {label} is not a list.")
    return payload
