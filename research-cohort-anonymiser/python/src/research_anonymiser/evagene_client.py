"""Thin client for the Evagene REST endpoints this demo needs.

Three capabilities:
  - ``get_pedigree_detail``   GET  /api/pedigrees/{id}
  - ``create_pedigree``       POST /api/pedigrees
  - ``rebuild_pedigree``      orchestrates create + add-relative calls to
                              mirror an anonymised pedigree on the account.

The orchestration reuses the intake-form pattern so a third-party reader
comparing the two demos sees the same shape: create_pedigree, create
proband individual, add-individual-to-pedigree, designate_as_proband,
then ``add-relative`` per remaining individual in a stable BFS order.

The transport uses an injected :class:`HttpGateway`; tests supply a fake
implementation of :class:`EvageneApi` and never see the gateway at all.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol

from .http_gateway import HttpGateway, HttpMethod

_HTTP_OK_LOWER = 200
_HTTP_OK_UPPER = 300


class EvageneApiError(RuntimeError):
    """Raised when the Evagene API is unreachable or returns a non-2xx response."""


@dataclass(frozen=True)
class CreateIndividualArgs:
    display_name: str
    biological_sex: str


@dataclass(frozen=True)
class AddRelativeArgs:
    pedigree_id: str
    relative_of: str
    relative_type: str
    display_name: str
    biological_sex: str


class EvageneApi(Protocol):
    """Surface the writer depends on; tests substitute their own implementation."""

    def get_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]: ...

    def rebuild_pedigree(self, anonymised: dict[str, Any]) -> str: ...


class EvageneClient:
    def __init__(self, *, base_url: str, api_key: str, http: HttpGateway) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http

    # ---- Read path -------------------------------------------------------

    def get_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/pedigrees/{pedigree_id}", body=None)

    # ---- Write path ------------------------------------------------------

    def rebuild_pedigree(self, anonymised: dict[str, Any]) -> str:
        orchestrator = _RebuildOrchestrator(self, anonymised)
        return orchestrator.run()

    def create_pedigree(self, display_name: str) -> str:
        payload = self._request("POST", "/api/pedigrees", body={"display_name": display_name})
        return _require_str(payload, "id")

    def create_individual(self, args: CreateIndividualArgs) -> str:
        payload = self._request(
            "POST",
            "/api/individuals",
            body={"display_name": args.display_name, "biological_sex": args.biological_sex},
        )
        return _require_str(payload, "id")

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None:
        self._request_ignoring_body(
            "POST",
            f"/api/pedigrees/{pedigree_id}/individuals/{individual_id}",
            body={},
        )

    def designate_as_proband(self, individual_id: str) -> None:
        self._request_ignoring_body(
            "PATCH",
            f"/api/individuals/{individual_id}",
            body={"proband": 1},
        )

    def add_relative(self, args: AddRelativeArgs) -> str:
        payload = self._request(
            "POST",
            f"/api/pedigrees/{args.pedigree_id}/register/add-relative",
            body={
                "relative_of": args.relative_of,
                "relative_type": args.relative_type,
                "display_name": args.display_name,
                "biological_sex": args.biological_sex,
            },
        )
        individual = _require_dict(payload, "individual")
        return _require_str(individual, "id")

    def delete_pedigree(self, pedigree_id: str) -> None:
        self._request_ignoring_body("DELETE", f"/api/pedigrees/{pedigree_id}", body=None)

    # ---- Transport helpers ----------------------------------------------

    def _request(
        self,
        method: HttpMethod,
        path: str,
        *,
        body: dict[str, Any] | None,
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

    def _request_ignoring_body(
        self,
        method: HttpMethod,
        path: str,
        *,
        body: dict[str, Any] | None,
    ) -> None:
        """For endpoints whose success response carries no useful body."""
        self._send(method, path, body)

    def _send(self, method: HttpMethod, path: str, body: dict[str, Any] | None) -> Any:
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


class _RebuildOrchestrator:
    """Mirror an anonymised pedigree on the account using intake-form primitives.

    Finds the proband, creates it, then walks the egg graph breadth-first
    to add every other individual via one ``add-relative`` call apiece.
    Fallback relationships (``sibling`` / ``son`` / ``daughter``) are chosen
    based on sex and whether a parent or a child has already been added.
    """

    def __init__(self, client: EvageneClient, anonymised: dict[str, Any]) -> None:
        self._client = client
        self._anonymised = anonymised
        self._source_to_new_id: dict[str, str] = {}

    def run(self) -> str:
        proband = self._require_proband()
        pedigree_id = self._create_pedigree_and_proband(proband)
        self._add_remaining_relatives(pedigree_id, proband)
        return pedigree_id

    def _require_proband(self) -> dict[str, Any]:
        for individual in self._anonymised["individuals"]:
            if individual.get("proband"):
                proband: dict[str, Any] = individual
                return proband
        raise EvageneApiError(
            "Anonymised pedigree has no proband; --as-new-pedigree needs one."
        )

    def _create_pedigree_and_proband(self, proband: dict[str, Any]) -> str:
        pedigree_id = self._client.create_pedigree(self._anonymised.get("display_name") or "Anon")
        proband_new_id = self._client.create_individual(
            CreateIndividualArgs(
                display_name=proband["display_name"],
                biological_sex=proband["biological_sex"],
            )
        )
        self._client.add_individual_to_pedigree(pedigree_id, proband_new_id)
        self._client.designate_as_proband(proband_new_id)
        self._source_to_new_id[proband["id"]] = proband_new_id
        return pedigree_id

    def _add_remaining_relatives(self, pedigree_id: str, proband: dict[str, Any]) -> None:
        individuals_by_id = {
            individual["id"]: individual for individual in self._anonymised["individuals"]
        }
        parents_of, children_of = self._build_relationship_maps()

        queue: deque[str] = deque([proband["id"]])
        visited: set[str] = {proband["id"]}
        while queue:
            anchor = queue.popleft()
            for neighbour_id, relative_type in self._neighbours_of(
                anchor, parents_of, children_of, individuals_by_id
            ):
                if neighbour_id in visited:
                    continue
                visited.add(neighbour_id)
                neighbour = individuals_by_id[neighbour_id]
                new_id = self._client.add_relative(
                    AddRelativeArgs(
                        pedigree_id=pedigree_id,
                        relative_of=self._source_to_new_id[anchor],
                        relative_type=relative_type,
                        display_name=neighbour["display_name"],
                        biological_sex=neighbour["biological_sex"],
                    )
                )
                self._source_to_new_id[neighbour_id] = new_id
                queue.append(neighbour_id)

    def _build_relationship_maps(self) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        relationships_by_id = {
            relationship["id"]: relationship
            for relationship in self._anonymised["relationships"]
        }
        parents_of: dict[str, list[str]] = {}
        children_of: dict[str, list[str]] = {}
        for egg in self._anonymised["eggs"]:
            children = [egg["individual_id"]] if egg.get("individual_id") else list(
                egg.get("individual_ids") or []
            )
            relationship = relationships_by_id.get(egg.get("relationship_id"))
            if relationship is None:
                continue
            parents = list(relationship.get("members") or [])
            for child in children:
                parents_of.setdefault(child, []).extend(parents)
                for parent in parents:
                    children_of.setdefault(parent, []).append(child)
        return parents_of, children_of

    def _neighbours_of(
        self,
        anchor_id: str,
        parents_of: dict[str, list[str]],
        children_of: dict[str, list[str]],
        individuals_by_id: dict[str, dict[str, Any]],
    ) -> list[tuple[str, str]]:
        neighbours: list[tuple[str, str]] = []
        for parent_id in parents_of.get(anchor_id, []):
            parent = individuals_by_id[parent_id]
            neighbours.append((parent_id, _parent_relative_type(parent["biological_sex"])))
            for sibling_id in children_of.get(parent_id, []):
                if sibling_id == anchor_id:
                    continue
                sibling = individuals_by_id[sibling_id]
                neighbours.append((sibling_id, _sibling_relative_type(sibling["biological_sex"])))
        for child_id in children_of.get(anchor_id, []):
            child = individuals_by_id[child_id]
            neighbours.append((child_id, _child_relative_type(child["biological_sex"])))
        return neighbours


def _parent_relative_type(sex: str) -> str:
    return "mother" if sex == "female" else "father"


def _sibling_relative_type(sex: str) -> str:
    return "sister" if sex == "female" else "brother"


def _child_relative_type(sex: str) -> str:
    return "daughter" if sex == "female" else "son"


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
