from typing import Any

import pytest

from publication_figure_renderer.evagene_client import ApiError, EvageneClient

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"


class _StubResponse:
    def __init__(self, status_code: int, text: str, payload: Any = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no JSON payload set")
        return self._payload


class _RecordingGateway:
    def __init__(self, response: _StubResponse) -> None:
        self._response = response
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}

    def get(self, url: str, *, headers: dict[str, str]) -> _StubResponse:
        self.last_url = url
        self.last_headers = headers
        return self._response


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_fetch_pedigree_svg_hits_export_svg_and_returns_the_raw_body() -> None:
    gateway = _RecordingGateway(_StubResponse(200, "<svg xmlns=\"http://www.w3.org/2000/svg\"/>"))

    svg_text = _client(gateway).fetch_pedigree_svg(_PEDIGREE_ID)

    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/export.svg"
    )
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert gateway.last_headers["Accept"] == "image/svg+xml"
    assert svg_text == "<svg xmlns=\"http://www.w3.org/2000/svg\"/>"


def test_fetch_pedigree_svg_trims_trailing_slash_on_base_url() -> None:
    gateway = _RecordingGateway(_StubResponse(200, "<svg/>"))

    EvageneClient(
        base_url="https://evagene.example/",
        api_key="evg_test",
        http=gateway,
    ).fetch_pedigree_svg(_PEDIGREE_ID)

    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/export.svg"
    )


def test_fetch_pedigree_svg_raises_on_non_2xx() -> None:
    gateway = _RecordingGateway(_StubResponse(500, "boom"))

    with pytest.raises(ApiError):
        _client(gateway).fetch_pedigree_svg(_PEDIGREE_ID)


def test_fetch_pedigree_detail_returns_parsed_json() -> None:
    gateway = _RecordingGateway(
        _StubResponse(200, "ignored", payload={"id": "abc", "individuals": []}),
    )

    detail = _client(gateway).fetch_pedigree_detail(_PEDIGREE_ID)

    assert gateway.last_url == f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}"
    assert detail == {"id": "abc", "individuals": []}


def test_fetch_pedigree_detail_raises_on_non_object_payload() -> None:
    gateway = _RecordingGateway(_StubResponse(200, "ignored", payload=["not", "an", "object"]))

    with pytest.raises(ApiError):
        _client(gateway).fetch_pedigree_detail(_PEDIGREE_ID)
