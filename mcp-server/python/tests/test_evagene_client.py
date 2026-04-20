import json
from pathlib import Path
from typing import Any

import pytest

from evagene_mcp.evagene_client import ApiError, EvageneClient

from .fakes import RecordingGateway, StubResponse

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_PEDIGREE_ID = "3d7b9b2e-4f3a-4b2d-9a1c-2e0a2b3c4d5e"
_COUNSELEE_ID = "11111111-1111-1111-1111-111111111111"


def _load_fixture(name: str) -> Any:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _client(gateway: RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def _always(response: StubResponse) -> RecordingGateway:
    return RecordingGateway(lambda _m, _u: response)


async def test_list_pedigrees_returns_parsed_array() -> None:
    gateway = _always(StubResponse(200, _load_fixture("sample-list-pedigrees.json")))

    result = await _client(gateway).list_pedigrees()

    assert gateway.calls[0].method == "GET"
    assert gateway.calls[0].url == "https://evagene.example/api/pedigrees"
    assert gateway.calls[0].headers["X-API-Key"] == "evg_test"
    assert len(result) == 2


async def test_get_pedigree_hits_the_right_url() -> None:
    gateway = _always(StubResponse(200, _load_fixture("sample-pedigree-detail.json")))

    await _client(gateway).get_pedigree(_PEDIGREE_ID)

    assert gateway.calls[0].url == f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}"


async def test_describe_pedigree_returns_text_body() -> None:
    gateway = _always(StubResponse(200, payload=None, text_body="A two-generation family..."))

    result = await _client(gateway).describe_pedigree(_PEDIGREE_ID)

    assert result == "A two-generation family..."
    assert gateway.calls[0].url.endswith(f"/api/pedigrees/{_PEDIGREE_ID}/describe")


async def test_calculate_risk_sends_model_and_counselee() -> None:
    gateway = _always(StubResponse(200, _load_fixture("sample-risk-nice.json")))

    await _client(gateway).calculate_risk(
        _PEDIGREE_ID, model="NICE", counselee_id=_COUNSELEE_ID,
    )

    call = gateway.calls[0]
    assert call.method == "POST"
    assert call.url.endswith(f"/api/pedigrees/{_PEDIGREE_ID}/risk/calculate")
    assert call.body == {"model": "NICE", "counselee_id": _COUNSELEE_ID}


async def test_calculate_risk_omits_counselee_when_absent() -> None:
    gateway = _always(StubResponse(200, _load_fixture("sample-risk-nice.json")))

    await _client(gateway).calculate_risk(_PEDIGREE_ID, model="NICE")

    assert gateway.calls[0].body == {"model": "NICE"}


async def test_list_risk_models_returns_object() -> None:
    gateway = _always(StubResponse(200, _load_fixture("sample-risk-models.json")))

    result = await _client(gateway).list_risk_models(_PEDIGREE_ID)

    assert "models" in result
    assert gateway.calls[0].url.endswith(f"/api/pedigrees/{_PEDIGREE_ID}/risk/models")


async def test_add_relative_posts_register_endpoint() -> None:
    gateway = _always(StubResponse(201, _load_fixture("sample-add-relative.json")))

    await _client(gateway).add_relative(
        _PEDIGREE_ID,
        relative_of=_COUNSELEE_ID,
        relative_type="sister",
        display_name="Jane",
        biological_sex="female",
    )

    call = gateway.calls[0]
    assert call.url.endswith(f"/api/pedigrees/{_PEDIGREE_ID}/register/add-relative")
    assert call.body == {
        "relative_of": _COUNSELEE_ID,
        "relative_type": "sister",
        "display_name": "Jane",
        "biological_sex": "female",
    }


async def test_raises_api_error_on_non_2xx() -> None:
    gateway = _always(StubResponse(500, {}))

    with pytest.raises(ApiError):
        await _client(gateway).list_pedigrees()
