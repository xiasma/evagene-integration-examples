from pathlib import Path

import pytest

from canrisk_bridge.canrisk_client import (
    CANRISK_HEADER,
    ApiError,
    CanRiskClient,
    CanRiskFormatError,
)

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _sample_canrisk() -> str:
    return (FIXTURES / "sample-canrisk.txt").read_text(encoding="utf-8")


class _StubResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class _RecordingGateway:
    def __init__(self, response: _StubResponse) -> None:
        self._response = response
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}

    def get_text(self, url: str, *, headers: dict[str, str]) -> _StubResponse:
        self.last_url = url
        self.last_headers = headers
        return self._response


def _client(gateway: _RecordingGateway) -> CanRiskClient:
    return CanRiskClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_gets_canrisk_endpoint_with_correct_headers() -> None:
    gateway = _RecordingGateway(_StubResponse(200, _sample_canrisk()))

    body = _client(gateway).fetch(_PEDIGREE_ID)

    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/risk/canrisk"
    )
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert gateway.last_headers["Accept"] == "text/tab-separated-values"
    assert body.startswith(CANRISK_HEADER)


def test_raises_api_error_on_non_2xx() -> None:
    gateway = _RecordingGateway(_StubResponse(500, ""))

    with pytest.raises(ApiError):
        _client(gateway).fetch(_PEDIGREE_ID)


def test_raises_format_error_when_header_missing() -> None:
    gateway = _RecordingGateway(_StubResponse(200, "not a canrisk file"))

    with pytest.raises(CanRiskFormatError):
        _client(gateway).fetch(_PEDIGREE_ID)
