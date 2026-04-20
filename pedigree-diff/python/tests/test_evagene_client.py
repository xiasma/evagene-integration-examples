from typing import Any

import pytest

from pedigree_diff.evagene_client import ApiError, EvageneClient

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"


class _StubResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _RecordingGateway:
    def __init__(self, response: _StubResponse) -> None:
        self._response = response
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}

    def get_json(self, url: str, *, headers: dict[str, str]) -> _StubResponse:
        self.last_url = url
        self.last_headers = headers
        return self._response


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_gets_pedigree_detail_from_documented_endpoint() -> None:
    gateway = _RecordingGateway(_StubResponse(200, {"id": _PEDIGREE_ID, "individuals": []}))

    payload = _client(gateway).get_pedigree_detail(_PEDIGREE_ID)

    assert gateway.last_url == f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}"
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert payload["id"] == _PEDIGREE_ID


def test_raises_api_error_on_non_2xx() -> None:
    gateway = _RecordingGateway(_StubResponse(404, {}))

    with pytest.raises(ApiError):
        _client(gateway).get_pedigree_detail(_PEDIGREE_ID)


def test_raises_api_error_on_non_object_payload() -> None:
    gateway = _RecordingGateway(_StubResponse(200, ["not", "an", "object"]))

    with pytest.raises(ApiError):
        _client(gateway).get_pedigree_detail(_PEDIGREE_ID)
