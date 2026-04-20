"""Narrow Evagene REST client covering only the calls this demo needs.

Each method wraps one endpoint and raises :class:`ApiError` with a
diagnostic that names the URL, not just a status code. The full API
surface lives in the OpenAPI spec at https://evagene.net/docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .genome_file import BiologicalSex
from .http_gateway import HttpGateway, HttpResponse

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


@dataclass(frozen=True)
class Individual:
    id: str
    display_name: str


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

    # --- Pedigrees ------------------------------------------------------

    def create_pedigree(self, display_name: str) -> str:
        """Create a scratch pedigree and return its UUID."""
        payload = self._post("/api/pedigrees", body={"display_name": display_name})
        return _require_id(payload, where="create_pedigree response")

    def delete_pedigree(self, pedigree_id: str) -> None:
        self._delete(f"/api/pedigrees/{pedigree_id}")

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None:
        self._post(
            f"/api/pedigrees/{pedigree_id}/individuals/{individual_id}",
            body=None,
            expect_body=False,
        )

    # --- Individuals ----------------------------------------------------

    def create_individual(
        self,
        *,
        display_name: str,
        biological_sex: BiologicalSex,
    ) -> Individual:
        body: dict[str, Any] = {"display_name": display_name}
        if biological_sex is not BiologicalSex.UNKNOWN:
            body["biological_sex"] = biological_sex.value
        payload = self._post("/api/individuals", body=body)
        return Individual(
            id=_require_id(payload, where="create_individual response"),
            display_name=display_name,
        )

    def delete_individual(self, individual_id: str) -> None:
        self._delete(f"/api/individuals/{individual_id}")

    def import_23andme_raw(self, *, pedigree_id: str, individual_id: str, tsv: str) -> None:
        """Upload a raw 23andMe genotype TSV to the named individual.

        The target individual is passed as the ``individual_id`` query
        parameter (not in the JSON body) — verified against Evagene
        v1 at the time of writing.
        """
        self._post(
            f"/api/pedigrees/{pedigree_id}/import/23andme-raw",
            body={"content": tsv},
            params={"individual_id": individual_id},
        )

    def find_ancestry_id_by_population_key(self, population_key: str) -> str | None:
        """Look up an ancestry UUID by its ``population_key`` (e.g. ``mediterranean``)."""
        url = f"{self._base_url}/api/ancestries"
        response = self._http.get_json(url, headers=self._headers())
        self._raise_for_status(response, url)
        try:
            payload = response.json()
        except ValueError as error:
            raise ApiError(f"Evagene API returned invalid JSON for {url}: {error}") from error
        if not isinstance(payload, list):
            raise ApiError(f"Expected a list from {url}, got {type(payload).__name__}")
        for entry in payload:
            if isinstance(entry, dict) and entry.get("population_key") == population_key:
                identifier = entry.get("id")
                if isinstance(identifier, str):
                    return identifier
        return None

    def add_ancestry_to_individual(
        self,
        *,
        individual_id: str,
        ancestry_id: str,
        proportion: float = 1.0,
    ) -> None:
        self._post(
            f"/api/individuals/{individual_id}/ancestries",
            body={"ancestry_id": ancestry_id, "proportion": proportion},
        )

    def get_population_risks(self, individual_id: str) -> dict[str, Any]:
        return self._get(f"/api/individuals/{individual_id}/population-risks")

    # --- Transport helpers ---------------------------------------------

    def _post(
        self,
        path: str,
        *,
        body: dict[str, Any] | None,
        params: dict[str, str] | None = None,
        expect_body: bool = True,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        response = self._http.post_json(url, headers=self._headers(), body=body, params=params)
        self._raise_for_status(response, url)
        return _parse_json_object(response, url) if expect_body else {}

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        response = self._http.get_json(url, headers=self._headers())
        self._raise_for_status(response, url)
        return _parse_json_object(response, url)

    def _delete(self, path: str) -> None:
        url = f"{self._base_url}{path}"
        response = self._http.delete(url, headers=self._headers())
        self._raise_for_status(response, url)

    @staticmethod
    def _raise_for_status(response: HttpResponse, url: str) -> None:
        if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
            raise ApiError(
                f"Evagene API returned HTTP {response.status_code} for {url}: "
                f"{_truncate(response.text)}",
            )

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


def _parse_json_object(response: HttpResponse, url: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as error:
        raise ApiError(f"Evagene API returned invalid JSON for {url}: {error}") from error
    if not isinstance(payload, dict):
        raise ApiError(
            f"Evagene API returned non-object JSON for {url}: {type(payload).__name__}",
        )
    return payload


def _require_id(payload: dict[str, Any], *, where: str) -> str:
    identifier = payload.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ApiError(f"{where} lacks a string 'id' field")
    return identifier


def _truncate(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."
