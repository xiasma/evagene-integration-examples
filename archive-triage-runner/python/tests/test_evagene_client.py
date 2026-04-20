from dataclasses import dataclass, field
from typing import Any

import pytest

from archive_triage.evagene_client import EvageneApiError, EvageneClient
from archive_triage.http_gateway import HttpMethod


@dataclass
class _Call:
    method: HttpMethod
    url: str
    headers: dict[str, str]
    body: dict[str, Any] | None


class _StubResponse:
    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


@dataclass
class _RecordingGateway:
    responses: list[_StubResponse]
    calls: list[_Call] = field(default_factory=list)

    def send(
        self,
        method: HttpMethod,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> _StubResponse:
        self.calls.append(_Call(method, url, headers, body))
        return self.responses.pop(0)


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_create_pedigree_posts_display_name_and_returns_id() -> None:
    gateway = _RecordingGateway(responses=[_StubResponse(201, {"id": "pedigree-1"})])

    pedigree_id = _client(gateway).create_pedigree("Smith family")

    call = gateway.calls[0]
    assert call.method == "POST"
    assert call.url == "https://evagene.example/api/pedigrees"
    assert call.body == {"display_name": "Smith family"}
    assert call.headers["X-API-Key"] == "evg_test"
    assert pedigree_id == "pedigree-1"


def test_import_gedcom_wraps_text_in_json_content_field() -> None:
    gateway = _RecordingGateway(responses=[_StubResponse(204)])

    _client(gateway).import_gedcom("pedigree-1", "0 HEAD\n0 TRLR\n")

    call = gateway.calls[0]
    assert call.url == "https://evagene.example/api/pedigrees/pedigree-1/import/gedcom"
    assert call.body == {"content": "0 HEAD\n0 TRLR\n"}


def test_has_proband_true_when_any_individual_has_nonzero_proband() -> None:
    detail = {
        "individuals": [
            {"id": "i1", "proband": 0},
            {"id": "i2", "proband": 90},
        ],
    }
    gateway = _RecordingGateway(responses=[_StubResponse(200, detail)])

    assert _client(gateway).has_proband("pedigree-1") is True


def test_has_proband_false_when_all_probands_zero() -> None:
    detail = {"individuals": [{"id": "i1", "proband": 0}]}
    gateway = _RecordingGateway(responses=[_StubResponse(200, detail)])

    assert _client(gateway).has_proband("pedigree-1") is False


def test_calculate_nice_posts_model_nice_and_returns_payload() -> None:
    gateway = _RecordingGateway(
        responses=[_StubResponse(200, {"cancer_risk": {"nice_category": "moderate"}})],
    )

    payload = _client(gateway).calculate_nice("pedigree-1")

    call = gateway.calls[0]
    assert call.url == "https://evagene.example/api/pedigrees/pedigree-1/risk/calculate"
    assert call.body == {"model": "NICE"}
    assert payload["cancer_risk"]["nice_category"] == "moderate"


def test_delete_pedigree_sends_delete() -> None:
    gateway = _RecordingGateway(responses=[_StubResponse(204)])

    _client(gateway).delete_pedigree("pedigree-1")

    call = gateway.calls[0]
    assert call.method == "DELETE"
    assert call.url == "https://evagene.example/api/pedigrees/pedigree-1"


def test_non_2xx_status_is_api_error() -> None:
    gateway = _RecordingGateway(responses=[_StubResponse(500)])

    with pytest.raises(EvageneApiError, match="HTTP 500"):
        _client(gateway).create_pedigree("Smith family")


def test_transport_failure_is_api_error() -> None:
    class _ExplodingGateway:
        def send(
            self,
            method: HttpMethod,
            url: str,
            *,
            headers: dict[str, str],
            body: dict[str, Any] | None = None,
        ) -> _StubResponse:
            raise OSError("DNS failed")

    with pytest.raises(EvageneApiError, match="unreachable"):
        EvageneClient(
            base_url="https://evagene.example",
            api_key="evg_test",
            http=_ExplodingGateway(),
        ).create_pedigree("Smith family")
