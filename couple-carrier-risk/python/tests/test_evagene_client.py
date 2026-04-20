from dataclasses import dataclass, field
from typing import Any

import pytest

from couple_carrier_risk.evagene_client import ApiError, EvageneClient
from couple_carrier_risk.genome_file import BiologicalSex


class _StubResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@dataclass
class _Call:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    params: dict[str, str] | None = None


class _RecordingGateway:
    def __init__(self, queue: list[_StubResponse]) -> None:
        self._queue = queue
        self.calls: list[_Call] = []

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> _StubResponse:
        self.calls.append(_Call("POST", url, headers, body, params))
        return self._queue.pop(0)

    def get_json(self, url: str, *, headers: dict[str, str]) -> _StubResponse:
        self.calls.append(_Call("GET", url, headers))
        return self._queue.pop(0)

    def delete(self, url: str, *, headers: dict[str, str]) -> _StubResponse:
        self.calls.append(_Call("DELETE", url, headers))
        return self._queue.pop(0)


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(
        base_url="https://evagene.example",
        api_key="evg_test",
        http=gateway,
    )


def test_create_pedigree_posts_display_name_and_returns_id() -> None:
    gateway = _RecordingGateway([
        _StubResponse(201, {"id": "ped-uuid", "display_name": "X"}),
    ])

    pedigree_id = _client(gateway).create_pedigree("scratch")

    assert pedigree_id == "ped-uuid"
    call = gateway.calls[0]
    assert call.method == "POST"
    assert call.url == "https://evagene.example/api/pedigrees"
    assert call.body == {"display_name": "scratch"}
    assert call.headers["X-API-Key"] == "evg_test"


def test_create_individual_maps_biological_sex_and_returns_record() -> None:
    gateway = _RecordingGateway([_StubResponse(201, {"id": "ind-uuid"})])

    individual = _client(gateway).create_individual(
        display_name="Partner A",
        biological_sex=BiologicalSex.MALE,
    )

    assert individual.id == "ind-uuid"
    assert gateway.calls[0].body == {"display_name": "Partner A", "biological_sex": "male"}


def test_create_individual_omits_biological_sex_when_unknown() -> None:
    gateway = _RecordingGateway([_StubResponse(201, {"id": "ind-uuid"})])

    _client(gateway).create_individual(
        display_name="Partner A",
        biological_sex=BiologicalSex.UNKNOWN,
    )

    assert gateway.calls[0].body == {"display_name": "Partner A"}


def test_add_individual_to_pedigree_posts_empty_body_at_correct_url() -> None:
    gateway = _RecordingGateway([_StubResponse(204, text="")])

    _client(gateway).add_individual_to_pedigree("ped-id", "ind-id")

    call = gateway.calls[0]
    assert call.method == "POST"
    assert call.url == "https://evagene.example/api/pedigrees/ped-id/individuals/ind-id"
    assert call.body is None


def test_import_23andme_raw_puts_individual_id_in_query_and_tsv_in_body() -> None:
    gateway = _RecordingGateway([_StubResponse(200, {"individual_id": "ind-id"})])

    _client(gateway).import_23andme_raw(
        pedigree_id="ped-id",
        individual_id="ind-id",
        tsv="# synthetic\nrs334\t11\t5248232\tAT\n",
    )

    call = gateway.calls[0]
    assert call.url == "https://evagene.example/api/pedigrees/ped-id/import/23andme-raw"
    assert call.params == {"individual_id": "ind-id"}
    assert call.body == {"content": "# synthetic\nrs334\t11\t5248232\tAT\n"}


def test_get_population_risks_returns_parsed_payload() -> None:
    payload = {"individual_id": "ind-id", "risks": []}
    gateway = _RecordingGateway([_StubResponse(200, payload)])

    result = _client(gateway).get_population_risks("ind-id")

    assert result == payload
    assert gateway.calls[0].method == "GET"
    assert gateway.calls[0].url == (
        "https://evagene.example/api/individuals/ind-id/population-risks"
    )


def test_find_ancestry_by_population_key_returns_id_when_present() -> None:
    gateway = _RecordingGateway([_StubResponse(200, [
        {"id": "anc-1", "population_key": "general"},
        {"id": "anc-2", "population_key": "mediterranean"},
    ])])

    result = _client(gateway).find_ancestry_id_by_population_key("mediterranean")

    assert result == "anc-2"


def test_find_ancestry_by_population_key_returns_none_when_absent() -> None:
    gateway = _RecordingGateway([_StubResponse(200, [{"id": "anc-1", "population_key": "x"}])])

    assert _client(gateway).find_ancestry_id_by_population_key("unknown") is None


def test_delete_pedigree_and_individual_hit_the_right_urls() -> None:
    gateway = _RecordingGateway([_StubResponse(204), _StubResponse(204)])
    client = _client(gateway)

    client.delete_individual("ind-id")
    client.delete_pedigree("ped-id")

    assert gateway.calls[0].method == "DELETE"
    assert gateway.calls[0].url == "https://evagene.example/api/individuals/ind-id"
    assert gateway.calls[1].url == "https://evagene.example/api/pedigrees/ped-id"


def test_non_2xx_status_raises_api_error_with_url_in_message() -> None:
    gateway = _RecordingGateway([_StubResponse(500, text="server boom")])

    with pytest.raises(ApiError, match="HTTP 500"):
        _client(gateway).get_population_risks("ind-id")


def test_non_object_payload_raises_api_error() -> None:
    gateway = _RecordingGateway([_StubResponse(200, ["not", "an", "object"])])

    with pytest.raises(ApiError, match="non-object"):
        _client(gateway).get_population_risks("ind-id")
