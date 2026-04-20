"""Thin Evagene REST client tailored for the notebook narrative.

Five operations, one per notebook need:

* :meth:`EvageneClient.get_pedigrees` — list the user's pedigrees.
* :meth:`EvageneClient.run_risk`     — one ``POST /risk/calculate`` call.
* :meth:`EvageneClient.clone_pedigree_for_exploration` — copy a pedigree
  into a scratch duplicate the notebook can safely mutate.
* :meth:`EvageneClient.delete_pedigree` — bin the scratch copy.
* :meth:`EvageneClient.evagene_url` — a shareable deep-link (no auth
  tokens; suitable to print in a cell output).

The client holds no mutable state of its own.  Every method is idempotent
from the client's point of view, which keeps the notebook predictable.
"""

from __future__ import annotations

import time
from typing import Any

from .http_gateway import HttpGateway, HttpResponse

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300
_HTTP_TOO_MANY_REQUESTS = 429
_SCRATCH_PREFIX = "[scratch] notebook-explorer"


class ApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


class EvageneClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        http: HttpGateway,
        rate_limit_sleeper: Any = time.sleep,
        rate_limit_wait_seconds: float = 5.0,
        rate_limit_max_retries: int = 12,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http
        self._sleep = rate_limit_sleeper
        self._rate_wait = rate_limit_wait_seconds
        self._rate_retries = rate_limit_max_retries

    # --------------------------------------------------------- discovery

    def get_pedigrees(self) -> list[dict[str, Any]]:
        """Return the caller's pedigrees (as the server shapes them)."""
        response = self._get("/api/pedigrees")
        payload = response.json()
        if not isinstance(payload, list):
            raise ApiError("Expected a JSON array from GET /api/pedigrees.")
        return payload

    # --------------------------------------------------------- risk

    def run_risk(
        self,
        pedigree_id: str,
        model: str,
        **body: Any,
    ) -> dict[str, Any]:
        """Run one risk calculation.  ``**body`` is merged into the request."""
        payload: dict[str, Any] = {"model": model, **body}
        response = self._post(
            f"/api/pedigrees/{pedigree_id}/risk/calculate",
            json_body=payload,
        )
        result = response.json()
        if not isinstance(result, dict):
            raise ApiError(f"Expected a JSON object from risk/calculate for model {model}.")
        return result

    # --------------------------------------------------------- scratch pedigree

    def clone_pedigree_for_exploration(
        self,
        source_pedigree_id: str,
        *,
        scratch_suffix: str,
    ) -> str:
        """Duplicate a pedigree via GEDCOM round-trip; return the scratch ID.

        The Evagene API has no single-call clone endpoint, so the sequence is:

        1. ``GET  /api/pedigrees/{source}/export.ged`` — export source as GEDCOM.
        2. ``POST /api/pedigrees``                     — create an empty target.
        3. ``POST /api/pedigrees/{target}/import/gedcom`` — import the text.

        Kept together here so the notebook sees one step.
        """
        gedcom_text = self._export_gedcom(source_pedigree_id)
        target_id = self._create_empty_pedigree(display_name=f"{_SCRATCH_PREFIX} {scratch_suffix}")
        self._import_gedcom(target_id, gedcom_text)
        return target_id

    def delete_pedigree(self, pedigree_id: str) -> None:
        """Remove a pedigree.  Called in the notebook's cleanup cell."""
        self._request("DELETE", f"/api/pedigrees/{pedigree_id}", json_body=None)

    # --------------------------------------------------------- mutation helpers

    def add_relative(
        self,
        pedigree_id: str,
        *,
        relative_of: str,
        relative_type: str,
        display_name: str,
        biological_sex: str | None = None,
    ) -> dict[str, Any]:
        """Add a new individual by relationship type and return the server result."""
        body: dict[str, Any] = {
            "relative_of": relative_of,
            "relative_type": relative_type,
            "display_name": display_name,
        }
        if biological_sex is not None:
            body["biological_sex"] = biological_sex
        response = self._post(
            f"/api/pedigrees/{pedigree_id}/register/add-relative",
            json_body=body,
        )
        result = response.json()
        if not isinstance(result, dict):
            raise ApiError("Expected a JSON object from add-relative.")
        return result

    def add_disease_to_individual(
        self,
        individual_id: str,
        *,
        disease_id: str,
        affection_status: str = "affected",
        age_at_diagnosis: int | None = None,
    ) -> None:
        """Record a disease against an individual (e.g. affected sister)."""
        body: dict[str, Any] = {
            "disease_id": disease_id,
            "affection_status": affection_status,
        }
        if age_at_diagnosis is not None:
            body["age_at_diagnosis"] = age_at_diagnosis
        self._post(f"/api/individuals/{individual_id}/diseases", json_body=body)

    def add_disease_to_pedigree(self, pedigree_id: str, disease_id: str) -> None:
        """Add a disease to the pedigree's working set so MF calculations pick it up."""
        self._post(
            f"/api/pedigrees/{pedigree_id}/diseases/{disease_id}",
            json_body={},
        )

    def patch_individual(self, individual_id: str, **fields: Any) -> None:
        """Update selected fields on an individual (e.g. ``age_at_menarche``).

        Used by the TC section to vary the proband's reproductive history on
        the scratch pedigree, since ``/risk/calculate`` reads those fields
        from the individual record rather than the request body.
        """
        self._request(
            "PATCH",
            f"/api/individuals/{individual_id}",
            json_body=dict(fields),
        )

    def get_register(self, pedigree_id: str) -> dict[str, Any]:
        """Return the pedigree's ``RegisterData`` (proband ID, rows, columns)."""
        response = self._get(f"/api/pedigrees/{pedigree_id}/register")
        payload = response.json()
        if not isinstance(payload, dict):
            raise ApiError("Expected a JSON object from /register.")
        return payload

    # --------------------------------------------------------- shareable links

    def evagene_url(self, pedigree_id: str) -> str:
        """Return a link to the pedigree in the web UI.  No credentials embedded."""
        return f"{self._base_url}/pedigrees/{pedigree_id}"

    # --------------------------------------------------------- internal plumbing

    def _export_gedcom(self, pedigree_id: str) -> str:
        response = self._get(f"/api/pedigrees/{pedigree_id}/export.ged")
        return response.text

    def _create_empty_pedigree(self, *, display_name: str) -> str:
        response = self._post("/api/pedigrees", json_body={"display_name": display_name})
        payload = response.json()
        pedigree_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(pedigree_id, str):
            raise ApiError("POST /api/pedigrees did not return an 'id' string.")
        return pedigree_id

    def _import_gedcom(self, pedigree_id: str, gedcom_text: str) -> None:
        self._post(
            f"/api/pedigrees/{pedigree_id}/import/gedcom",
            json_body={"content": gedcom_text},
        )

    def _get(self, path: str) -> HttpResponse:
        return self._request("GET", path, json_body=None)

    def _post(self, path: str, *, json_body: dict[str, Any]) -> HttpResponse:
        return self._request("POST", path, json_body=json_body)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None,
    ) -> HttpResponse:
        url = f"{self._base_url}{path}"
        for _ in range(self._rate_retries + 1):
            response = self._http.request(
                method, url, headers=self._headers(), json_body=json_body
            )
            if response.status_code == _HTTP_TOO_MANY_REQUESTS:
                self._sleep(self._rate_wait)
                continue
            if not _HTTP_OK_LOWER <= response.status_code < _HTTP_OK_UPPER:
                raise ApiError(
                    f"Evagene API returned HTTP {response.status_code} for {method} {path}"
                )
            return response
        raise ApiError(
            f"Evagene API still rate-limited after {self._rate_retries} retries for {method} {path}"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
