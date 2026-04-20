from typing import Any

import pytest

from bayesmendel_comparator.risk_api_client import ApiError, RiskApiClient

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_COUNSELEE_ID = "22222222-2222-2222-2222-222222222222"


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
        self.last_body: dict[str, Any] = {}

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> _StubResponse:
        self.last_url = url
        self.last_headers = headers
        self.last_body = body
        return self._response


def _client(gateway: _RecordingGateway) -> RiskApiClient:
    return RiskApiClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


@pytest.mark.parametrize("model", ["BRCAPRO", "MMRpro", "PancPRO"])
def test_posts_requested_model_to_risk_calculate(model: str) -> None:
    gateway = _RecordingGateway(
        _StubResponse(200, {"carrier_probabilities": {}, "future_risks": []}),
    )

    _client(gateway).calculate(_PEDIGREE_ID, model)

    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/risk/calculate"
    )
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert gateway.last_body == {"model": model}


def test_includes_counselee_when_provided() -> None:
    gateway = _RecordingGateway(_StubResponse(200, {}))

    _client(gateway).calculate(_PEDIGREE_ID, "BRCAPRO", counselee_id=_COUNSELEE_ID)

    assert gateway.last_body["counselee_id"] == _COUNSELEE_ID


def test_raises_api_error_on_non_2xx() -> None:
    gateway = _RecordingGateway(_StubResponse(500, {}))

    with pytest.raises(ApiError):
        _client(gateway).calculate(_PEDIGREE_ID, "BRCAPRO")


def test_raises_api_error_on_non_object_payload() -> None:
    gateway = _RecordingGateway(_StubResponse(200, ["not", "an", "object"]))

    with pytest.raises(ApiError):
        _client(gateway).calculate(_PEDIGREE_ID, "BRCAPRO")
