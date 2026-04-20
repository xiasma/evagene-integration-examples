from __future__ import annotations

from typing import Any

import pytest

from xeg_upgrader.evagene_client import EvageneApiError, EvageneClient
from xeg_upgrader.http_gateway import HttpMethod

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_XEG_XML = '<?xml version="1.0"?><Pedigree/>'


class _StubResponse:
    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no JSON body")
        return self._payload


class _RecordingGateway:
    def __init__(self, response: _StubResponse) -> None:
        self._response = response
        self.last_method: str = ""
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}
        self.last_body: dict[str, Any] | None = None

    def send(
        self,
        method: HttpMethod,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None,
    ) -> _StubResponse:
        self.last_method = method
        self.last_url = url
        self.last_headers = headers
        self.last_body = body
        return self._response


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_create_pedigree_posts_display_name_and_returns_id() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"id": _PEDIGREE_ID}))

    pedigree_id = _client(gateway).create_pedigree("Hill family")

    assert pedigree_id == _PEDIGREE_ID
    assert gateway.last_method == "POST"
    assert gateway.last_url == "https://evagene.example/api/pedigrees"
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert gateway.last_headers["Content-Type"] == "application/json"
    assert gateway.last_body == {"display_name": "Hill family"}


def test_parse_only_posts_to_xeg_endpoint_with_mode_parse() -> None:
    gateway = _RecordingGateway(
        _StubResponse(200, {"individuals": [], "relationships": [], "eggs": [], "diseases": []})
    )

    _client(gateway).import_xeg_parse_only(_PEDIGREE_ID, _XEG_XML)

    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/import/xeg?mode=parse"
    )
    assert gateway.last_body == {"content": _XEG_XML}


def test_import_posts_to_xeg_endpoint_without_mode_query() -> None:
    gateway = _RecordingGateway(_StubResponse(204))

    _client(gateway).import_xeg(_PEDIGREE_ID, _XEG_XML)

    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/import/xeg"
    )
    assert "mode=" not in gateway.last_url


def test_raises_on_non_2xx_status() -> None:
    gateway = _RecordingGateway(_StubResponse(500))

    with pytest.raises(EvageneApiError):
        _client(gateway).import_xeg(_PEDIGREE_ID, _XEG_XML)


def test_delete_pedigree_sends_delete_without_body() -> None:
    gateway = _RecordingGateway(_StubResponse(204))

    _client(gateway).delete_pedigree(_PEDIGREE_ID)

    assert gateway.last_method == "DELETE"
    assert gateway.last_url == f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}"
    assert gateway.last_body is None
