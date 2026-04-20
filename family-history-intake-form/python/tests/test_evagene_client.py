from typing import Any

import pytest

from family_intake.evagene_client import (
    AddRelativeArgs,
    CreateIndividualArgs,
    EvageneApiError,
    EvageneClient,
)
from family_intake.intake_submission import BiologicalSex

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_INDIVIDUAL_ID = "22222222-2222-2222-2222-222222222222"


class _StubResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _EmptyBodyResponse:
    """Mimics an Evagene response with an empty body: .json() raises, as httpx does."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def json(self) -> Any:
        raise ValueError("no JSON body")


class _RecordingGateway:
    def __init__(self, response: _StubResponse | _EmptyBodyResponse) -> None:
        self._response = response
        self.last_method: str = ""
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}
        self.last_body: dict[str, Any] = {}

    def send(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> _StubResponse | _EmptyBodyResponse:
        self.last_method = method
        self.last_url = url
        self.last_headers = headers
        self.last_body = body
        return self._response


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_create_pedigree_posts_display_name_and_returns_id() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"id": _PEDIGREE_ID}))

    pedigree_id = _client(gateway).create_pedigree("Emma's family")

    assert pedigree_id == _PEDIGREE_ID
    assert gateway.last_method == "POST"
    assert gateway.last_url == "https://evagene.example/api/pedigrees"
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert gateway.last_body == {"display_name": "Emma's family"}


def test_create_individual_includes_year_in_properties() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"id": _INDIVIDUAL_ID}))

    _client(gateway).create_individual(
        CreateIndividualArgs(
            display_name="Emma",
            biological_sex=BiologicalSex.FEMALE,
            year_of_birth=1985,
        )
    )

    assert gateway.last_body == {
        "display_name": "Emma",
        "biological_sex": "female",
        "properties": {"year_of_birth": 1985},
    }


def test_designate_as_proband_patches_individual() -> None:
    gateway = _RecordingGateway(_StubResponse(200, {"id": _INDIVIDUAL_ID}))

    _client(gateway).designate_as_proband(_INDIVIDUAL_ID)

    assert gateway.last_method == "PATCH"
    assert gateway.last_url == f"https://evagene.example/api/individuals/{_INDIVIDUAL_ID}"
    assert gateway.last_body == {"proband": 1}


def test_add_relative_returns_new_individual_id() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"individual": {"id": _INDIVIDUAL_ID}}))

    returned = _client(gateway).add_relative(
        AddRelativeArgs(
            pedigree_id=_PEDIGREE_ID,
            relative_of="proband-id",
            relative_type="mother",
            display_name="Grace",
            biological_sex=BiologicalSex.FEMALE,
        )
    )

    assert returned == _INDIVIDUAL_ID
    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/register/add-relative"
    )
    assert gateway.last_body == {
        "relative_of": "proband-id",
        "relative_type": "mother",
        "display_name": "Grace",
        "biological_sex": "female",
    }


def test_non_2xx_raises_api_error() -> None:
    gateway = _RecordingGateway(_StubResponse(500, {}))

    with pytest.raises(EvageneApiError):
        _client(gateway).create_pedigree("Emma's family")


def test_add_individual_to_pedigree_tolerates_empty_body() -> None:
    gateway = _RecordingGateway(_EmptyBodyResponse(204))

    _client(gateway).add_individual_to_pedigree(_PEDIGREE_ID, _INDIVIDUAL_ID)

    assert gateway.last_method == "POST"
    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/individuals/{_INDIVIDUAL_ID}"
    )
    assert gateway.last_body == {}


def test_designate_as_proband_tolerates_empty_body() -> None:
    gateway = _RecordingGateway(_EmptyBodyResponse(204))

    _client(gateway).designate_as_proband(_INDIVIDUAL_ID)

    assert gateway.last_method == "PATCH"
    assert gateway.last_url == f"https://evagene.example/api/individuals/{_INDIVIDUAL_ID}"
    assert gateway.last_body == {"proband": 1}


def test_missing_id_raises_api_error() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"not_id": "x"}))

    with pytest.raises(EvageneApiError):
        _client(gateway).create_pedigree("Emma's family")
