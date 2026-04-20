"""Tests for the thin Evagene REST client."""

from __future__ import annotations

from typing import Any

import pytest

from pedigree_puzzle.evagene_client import (
    AddRelativeArgs,
    CreateIndividualArgs,
    DiseaseNotFoundError,
    EvageneApiError,
    EvageneClient,
)
from pedigree_puzzle.inheritance import Sex

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_INDIVIDUAL_ID = "22222222-2222-2222-2222-222222222222"
_DISEASE_ID = "33333333-3333-3333-3333-333333333333"


class _StubResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no JSON body")
        return self._payload


class _ScriptedGateway:
    """Gateway that records every call and replies according to a script.

    The script is indexed by ``(method, url-ending)`` so tests do not need
    to repeat the full base URL.
    """

    def __init__(self, responses: dict[tuple[str, str], _StubResponse]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def send(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> _StubResponse:
        _ = headers, params
        self.calls.append((method, url, body))
        for (want_method, url_suffix), response in self._responses.items():
            if method == want_method and url.endswith(url_suffix):
                return response
        raise AssertionError(f"Unscripted request: {method} {url}")


def _client(gateway: _ScriptedGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_search_diseases_returns_matching_entry() -> None:
    gateway = _ScriptedGateway(
        {
            ("GET", "/api/diseases"): _StubResponse(
                200,
                [
                    {"id": "aaa", "display_name": "Some other disease"},
                    {"id": _DISEASE_ID, "display_name": "Cystic Fibrosis"},
                ],
            )
        }
    )

    summary = _client(gateway).search_diseases("cystic")

    assert summary.disease_id == _DISEASE_ID
    assert summary.display_name == "Cystic Fibrosis"


def test_search_diseases_prefers_exact_match_over_substring() -> None:
    gateway = _ScriptedGateway(
        {
            ("GET", "/api/diseases"): _StubResponse(
                200,
                [
                    {"id": "pulmonary", "display_name": "Cystic Fibrosis (Pulmonary)"},
                    {"id": _DISEASE_ID, "display_name": "Cystic Fibrosis"},
                ],
            )
        }
    )

    summary = _client(gateway).search_diseases("Cystic Fibrosis")

    assert summary.disease_id == _DISEASE_ID
    assert summary.display_name == "Cystic Fibrosis"


def test_search_diseases_raises_when_no_match() -> None:
    gateway = _ScriptedGateway(
        {("GET", "/api/diseases"): _StubResponse(200, [])}
    )

    with pytest.raises(DiseaseNotFoundError):
        _client(gateway).search_diseases("unobtainable")


def test_create_pedigree_posts_display_name_and_returns_id() -> None:
    gateway = _ScriptedGateway(
        {("POST", "/api/pedigrees"): _StubResponse(201, {"id": _PEDIGREE_ID})}
    )

    pedigree_id = _client(gateway).create_pedigree("Puzzle pedigree")

    assert pedigree_id == _PEDIGREE_ID
    method, url, body = gateway.calls[0]
    assert method == "POST"
    assert url.endswith("/api/pedigrees")
    assert body == {"display_name": "Puzzle pedigree"}


def test_create_individual_sends_sex_and_returns_id() -> None:
    gateway = _ScriptedGateway(
        {("POST", "/api/individuals"): _StubResponse(201, {"id": _INDIVIDUAL_ID})}
    )

    returned = _client(gateway).create_individual(
        CreateIndividualArgs(display_name="Person 1", sex=Sex.FEMALE)
    )

    assert returned == _INDIVIDUAL_ID
    _, _, body = gateway.calls[0]
    assert body == {"display_name": "Person 1", "biological_sex": "female"}


def test_add_individual_to_pedigree_tolerates_empty_body() -> None:
    gateway = _ScriptedGateway(
        {
            (
                "POST",
                f"/api/pedigrees/{_PEDIGREE_ID}/individuals/{_INDIVIDUAL_ID}",
            ): _StubResponse(204)
        }
    )

    _client(gateway).add_individual_to_pedigree(_PEDIGREE_ID, _INDIVIDUAL_ID)

    method, url, body = gateway.calls[0]
    assert method == "POST"
    assert url.endswith(f"/api/pedigrees/{_PEDIGREE_ID}/individuals/{_INDIVIDUAL_ID}")
    assert body == {}


def test_designate_as_proband_patches_with_proband_flag() -> None:
    gateway = _ScriptedGateway(
        {("PATCH", f"/api/individuals/{_INDIVIDUAL_ID}"): _StubResponse(204)}
    )

    _client(gateway).designate_as_proband(_INDIVIDUAL_ID)

    method, _, body = gateway.calls[0]
    assert method == "PATCH"
    assert body == {"proband": 1}


def test_add_relative_returns_new_individual_id() -> None:
    gateway = _ScriptedGateway(
        {
            (
                "POST",
                f"/api/pedigrees/{_PEDIGREE_ID}/register/add-relative",
            ): _StubResponse(201, {"individual": {"id": _INDIVIDUAL_ID}})
        }
    )

    returned = _client(gateway).add_relative(
        AddRelativeArgs(
            pedigree_id=_PEDIGREE_ID,
            relative_of="anchor-id",
            relative_type="mother",
            display_name="Person 2",
            sex=Sex.FEMALE,
        )
    )

    assert returned == _INDIVIDUAL_ID
    _, _, body = gateway.calls[0]
    assert body == {
        "relative_of": "anchor-id",
        "relative_type": "mother",
        "display_name": "Person 2",
        "biological_sex": "female",
    }


def test_add_disease_to_individual_posts_disease_id() -> None:
    gateway = _ScriptedGateway(
        {
            (
                "POST",
                f"/api/individuals/{_INDIVIDUAL_ID}/diseases",
            ): _StubResponse(201, {"disease_id": _DISEASE_ID})
        }
    )

    _client(gateway).add_disease_to_individual(_INDIVIDUAL_ID, _DISEASE_ID)

    _, _, body = gateway.calls[0]
    assert body == {"disease_id": _DISEASE_ID}


def test_get_pedigree_svg_returns_response_text() -> None:
    gateway = _ScriptedGateway(
        {
            (
                "GET",
                f"/api/pedigrees/{_PEDIGREE_ID}/export.svg",
            ): _StubResponse(200, text="<svg></svg>")
        }
    )

    svg = _client(gateway).get_pedigree_svg(_PEDIGREE_ID)

    assert svg == "<svg></svg>"


def test_delete_pedigree_sends_delete() -> None:
    gateway = _ScriptedGateway(
        {("DELETE", f"/api/pedigrees/{_PEDIGREE_ID}"): _StubResponse(204)}
    )

    _client(gateway).delete_pedigree(_PEDIGREE_ID)

    method, url, _ = gateway.calls[0]
    assert method == "DELETE"
    assert url.endswith(f"/api/pedigrees/{_PEDIGREE_ID}")


def test_non_2xx_raises_api_error() -> None:
    gateway = _ScriptedGateway(
        {("POST", "/api/pedigrees"): _StubResponse(500)}
    )

    with pytest.raises(EvageneApiError):
        _client(gateway).create_pedigree("Puzzle pedigree")


def test_missing_id_raises_api_error() -> None:
    gateway = _ScriptedGateway(
        {("POST", "/api/pedigrees"): _StubResponse(201, {"not_id": "x"})}
    )

    with pytest.raises(EvageneApiError):
        _client(gateway).create_pedigree("Puzzle pedigree")
