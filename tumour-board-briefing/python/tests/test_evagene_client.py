from __future__ import annotations

from typing import Any

import pytest

from tumour_board_briefing.evagene_client import ApiError, EvageneClient

_PEDIGREE = "11111111-1111-1111-1111-111111111111"
_COUNSELEE = "22222222-2222-2222-2222-222222222222"


class _StubResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: Any = None,
        content: bytes = b"",
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.text = text

    def json(self) -> Any:
        return self._payload


class _RecordingGateway:
    def __init__(self) -> None:
        self.get_calls: list[tuple[str, dict[str, str]]] = []
        self.post_calls: list[tuple[str, dict[str, str], dict[str, Any]]] = []
        self.next_get: _StubResponse = _StubResponse(payload={})
        self.next_post: _StubResponse = _StubResponse(payload={})

    def get(self, url: str, *, headers: dict[str, str]) -> _StubResponse:
        self.get_calls.append((url, headers))
        return self.next_get

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> _StubResponse:
        self.post_calls.append((url, headers, body))
        return self.next_post


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example/", api_key="evg_test", http=gateway)


def test_fetch_pedigree_detail_targets_documented_url() -> None:
    gateway = _RecordingGateway()
    gateway.next_get = _StubResponse(payload={"id": _PEDIGREE, "display_name": "x"})

    _client(gateway).fetch_pedigree_detail(_PEDIGREE)

    url, headers = gateway.get_calls[0]
    assert url == f"https://evagene.example/api/pedigrees/{_PEDIGREE}"
    assert headers["X-API-Key"] == "evg_test"
    assert headers["Accept"] == "application/json"


def test_fetch_pedigree_svg_targets_documented_url_and_returns_bytes() -> None:
    gateway = _RecordingGateway()
    gateway.next_get = _StubResponse(content=b"<svg/>")

    result = _client(gateway).fetch_pedigree_svg(_PEDIGREE)

    url, headers = gateway.get_calls[0]
    assert url == f"https://evagene.example/api/pedigrees/{_PEDIGREE}/export.svg"
    assert headers["Accept"] == "image/svg+xml"
    assert result == b"<svg/>"


@pytest.mark.parametrize(
    "model",
    ["CLAUS", "COUCH", "FRANK", "MANCHESTER", "NICE", "TYRER_CUZICK"],
)
def test_calculate_risk_posts_model_name(model: str) -> None:
    gateway = _RecordingGateway()
    gateway.next_post = _StubResponse(payload={"cancer_risk": {}})

    _client(gateway).calculate_risk(_PEDIGREE, model)

    url, _, body = gateway.post_calls[0]
    assert url == f"https://evagene.example/api/pedigrees/{_PEDIGREE}/risk/calculate"
    assert body == {"model": model}


def test_calculate_risk_includes_counselee_when_given() -> None:
    gateway = _RecordingGateway()
    gateway.next_post = _StubResponse(payload={"cancer_risk": {}})

    _client(gateway).calculate_risk(_PEDIGREE, "NICE", counselee_id=_COUNSELEE)

    _, _, body = gateway.post_calls[0]
    assert body == {"model": "NICE", "counselee_id": _COUNSELEE}


def test_non_2xx_raises_api_error() -> None:
    gateway = _RecordingGateway()
    gateway.next_get = _StubResponse(status_code=500, payload={})

    with pytest.raises(ApiError):
        _client(gateway).fetch_pedigree_detail(_PEDIGREE)


def test_non_object_json_raises_api_error() -> None:
    gateway = _RecordingGateway()
    gateway.next_post = _StubResponse(payload=["not", "an", "object"])

    with pytest.raises(ApiError):
        _client(gateway).calculate_risk(_PEDIGREE, "NICE")
