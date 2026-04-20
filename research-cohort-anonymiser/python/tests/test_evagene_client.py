from typing import Any

import pytest

from research_anonymiser.evagene_client import (
    EvageneApiError,
    EvageneClient,
)

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_INDIVIDUAL_ID = "22222222-2222-2222-2222-222222222222"


class _StubResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _EmptyBodyResponse:
    """Mimics an empty-body HTTP response: .json() raises, as httpx does."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def json(self) -> Any:
        raise ValueError("empty body")


class _RecordingGateway:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.last_method: str = ""
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}
        self.last_body: dict[str, Any] | None = None

    def send(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None,
    ) -> Any:
        self.last_method = method
        self.last_url = url
        self.last_headers = headers
        self.last_body = body
        return self._response


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_get_pedigree_detail_returns_parsed_json() -> None:
    gateway = _RecordingGateway(_StubResponse(200, {"id": _PEDIGREE_ID, "individuals": []}))

    detail = _client(gateway).get_pedigree_detail(_PEDIGREE_ID)

    assert gateway.last_method == "GET"
    assert gateway.last_url == f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}"
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert detail["id"] == _PEDIGREE_ID


def test_non_2xx_raises_api_error() -> None:
    gateway = _RecordingGateway(_StubResponse(500, {}))

    with pytest.raises(EvageneApiError):
        _client(gateway).get_pedigree_detail(_PEDIGREE_ID)


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


def test_create_pedigree_returns_id() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"id": "new-ped-id"}))

    new_id = _client(gateway).create_pedigree("Anon family")

    assert new_id == "new-ped-id"
    assert gateway.last_body == {"display_name": "Anon family"}
