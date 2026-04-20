from dataclasses import dataclass, field
from typing import Any

import pytest

from notebook_explorer.client import ApiError, EvageneClient

_BASE_URL = "https://evagene.example"
_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_SCRATCH_ID = "99999999-9999-9999-9999-999999999999"
_INDIVIDUAL_ID = "22222222-2222-2222-2222-222222222222"
_RELATIVE_ID = "33333333-3333-3333-3333-333333333333"
_DISEASE_ID = "44444444-4444-4444-4444-444444444444"


@dataclass
class _Call:
    method: str
    url: str
    headers: dict[str, str]
    json_body: dict[str, Any] | None


class _StubResponse:
    def __init__(
        self,
        status_code: int,
        payload: Any = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self._text = text

    def json(self) -> Any:
        return self._payload

    @property
    def text(self) -> str:
        return self._text


@dataclass
class _ScriptedGateway:
    """Replies with a queue of responses; records every request for inspection."""

    responses: list[_StubResponse]
    calls: list[_Call] = field(default_factory=list)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
    ) -> _StubResponse:
        self.calls.append(_Call(method=method, url=url, headers=headers, json_body=json_body))
        if not self.responses:
            raise AssertionError(f"Unexpected extra call: {method} {url}")
        return self.responses.pop(0)


def _client(gateway: _ScriptedGateway) -> EvageneClient:
    return EvageneClient(
        base_url=_BASE_URL,
        api_key="evg_test",
        http=gateway,
        rate_limit_sleeper=lambda _seconds: None,
        rate_limit_wait_seconds=0.0,
    )


# ----------------------------------------------------------- get_pedigrees


def test_get_pedigrees_returns_the_list_from_the_api() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(200, [{"id": _PEDIGREE_ID}])])

    pedigrees = _client(gateway).get_pedigrees()

    assert pedigrees == [{"id": _PEDIGREE_ID}]
    call = gateway.calls[0]
    assert call.method == "GET"
    assert call.url == f"{_BASE_URL}/api/pedigrees"
    assert call.headers["X-API-Key"] == "evg_test"


def test_get_pedigrees_rejects_non_list_payload() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(200, {"not": "a list"})])

    with pytest.raises(ApiError):
        _client(gateway).get_pedigrees()


# ----------------------------------------------------------- run_risk


def test_run_risk_posts_model_and_extra_body() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(200, {"cancer_risk": {}})])

    _client(gateway).run_risk(_PEDIGREE_ID, "TYRER_CUZICK", age_at_menarche=12, parity=0)

    call = gateway.calls[0]
    assert call.method == "POST"
    assert call.url == f"{_BASE_URL}/api/pedigrees/{_PEDIGREE_ID}/risk/calculate"
    assert call.json_body == {"model": "TYRER_CUZICK", "age_at_menarche": 12, "parity": 0}


def test_run_risk_rejects_non_object_payload() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(200, ["nope"])])

    with pytest.raises(ApiError):
        _client(gateway).run_risk(_PEDIGREE_ID, "NICE")


def test_run_risk_raises_on_http_error() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(500, {})])

    with pytest.raises(ApiError):
        _client(gateway).run_risk(_PEDIGREE_ID, "NICE")


# ----------------------------------------------------------- clone sequence


def test_clone_pedigree_sequences_export_create_import() -> None:
    gateway = _ScriptedGateway(
        responses=[
            _StubResponse(200, text="0 HEAD\n0 TRLR\n"),
            _StubResponse(201, {"id": _SCRATCH_ID}),
            _StubResponse(204, {}),
        ],
    )

    scratch_id = _client(gateway).clone_pedigree_for_exploration(
        _PEDIGREE_ID, scratch_suffix="2026-04-20 12:00"
    )

    assert scratch_id == _SCRATCH_ID
    assert [(call.method, call.url) for call in gateway.calls] == [
        ("GET", f"{_BASE_URL}/api/pedigrees/{_PEDIGREE_ID}/export.ged"),
        ("POST", f"{_BASE_URL}/api/pedigrees"),
        ("POST", f"{_BASE_URL}/api/pedigrees/{_SCRATCH_ID}/import/gedcom"),
    ]
    create_body = gateway.calls[1].json_body
    assert create_body is not None
    assert create_body["display_name"].startswith("[scratch] notebook-explorer")
    import_body = gateway.calls[2].json_body
    assert import_body == {"content": "0 HEAD\n0 TRLR\n"}


def test_clone_pedigree_rejects_create_response_without_id() -> None:
    gateway = _ScriptedGateway(
        responses=[
            _StubResponse(200, text="0 HEAD\n0 TRLR\n"),
            _StubResponse(201, {"name": "no id here"}),
        ],
    )

    with pytest.raises(ApiError):
        _client(gateway).clone_pedigree_for_exploration(
            _PEDIGREE_ID, scratch_suffix="2026-04-20 12:00"
        )


# ----------------------------------------------------------- delete + mutate


def test_delete_pedigree_issues_delete_request() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(204, {})])

    _client(gateway).delete_pedigree(_SCRATCH_ID)

    call = gateway.calls[0]
    assert call.method == "DELETE"
    assert call.url == f"{_BASE_URL}/api/pedigrees/{_SCRATCH_ID}"


def test_add_relative_posts_to_register_endpoint() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(200, {"individual": {"id": _RELATIVE_ID}})])

    result = _client(gateway).add_relative(
        _SCRATCH_ID,
        relative_of=_INDIVIDUAL_ID,
        relative_type="sister",
        display_name="Scratch sister",
        biological_sex="female",
    )

    assert result == {"individual": {"id": _RELATIVE_ID}}
    call = gateway.calls[0]
    assert call.url == f"{_BASE_URL}/api/pedigrees/{_SCRATCH_ID}/register/add-relative"
    assert call.json_body == {
        "relative_of": _INDIVIDUAL_ID,
        "relative_type": "sister",
        "display_name": "Scratch sister",
        "biological_sex": "female",
    }


def test_add_disease_to_individual_posts_affection_and_age() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(201, {})])

    _client(gateway).add_disease_to_individual(
        _RELATIVE_ID,
        disease_id=_DISEASE_ID,
        age_at_diagnosis=42,
    )

    call = gateway.calls[0]
    assert call.url == f"{_BASE_URL}/api/individuals/{_RELATIVE_ID}/diseases"
    assert call.json_body == {
        "disease_id": _DISEASE_ID,
        "affection_status": "affected",
        "age_at_diagnosis": 42,
    }


# ----------------------------------------------------------- evagene_url


def test_evagene_url_is_credential_free() -> None:
    gateway = _ScriptedGateway(responses=[])

    url = _client(gateway).evagene_url(_PEDIGREE_ID)

    assert url == f"{_BASE_URL}/pedigrees/{_PEDIGREE_ID}"
    assert "evg_" not in url


def test_add_disease_to_pedigree_posts_to_working_set() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(201, {})])

    _client(gateway).add_disease_to_pedigree(_SCRATCH_ID, _DISEASE_ID)

    call = gateway.calls[0]
    assert call.method == "POST"
    assert call.url == f"{_BASE_URL}/api/pedigrees/{_SCRATCH_ID}/diseases/{_DISEASE_ID}"


def test_patch_individual_sends_fields_as_body() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(200, {})])

    _client(gateway).patch_individual(
        _INDIVIDUAL_ID, age_at_menarche=12, parity=2, breast_density_birads=3
    )

    call = gateway.calls[0]
    assert call.method == "PATCH"
    assert call.url == f"{_BASE_URL}/api/individuals/{_INDIVIDUAL_ID}"
    assert call.json_body == {
        "age_at_menarche": 12,
        "parity": 2,
        "breast_density_birads": 3,
    }


def test_retries_on_rate_limit_until_success() -> None:
    gateway = _ScriptedGateway(
        responses=[
            _StubResponse(429, {}),
            _StubResponse(429, {}),
            _StubResponse(200, [{"id": _PEDIGREE_ID}]),
        ],
    )

    pedigrees = _client(gateway).get_pedigrees()

    assert pedigrees == [{"id": _PEDIGREE_ID}]
    assert len(gateway.calls) == 3


def test_retries_on_rate_limit_honour_max_retries() -> None:
    gateway = _ScriptedGateway(responses=[_StubResponse(429, {})] * 20)

    client = EvageneClient(
        base_url=_BASE_URL,
        api_key="evg_test",
        http=gateway,
        rate_limit_sleeper=lambda _seconds: None,
        rate_limit_wait_seconds=0.0,
        rate_limit_max_retries=3,
    )

    with pytest.raises(ApiError, match="rate-limited"):
        client.get_pedigrees()
    assert len(gateway.calls) == 4  # one initial attempt + 3 retries


def test_get_register_returns_server_object() -> None:
    gateway = _ScriptedGateway(
        responses=[_StubResponse(200, {"proband_id": _INDIVIDUAL_ID, "rows": []})]
    )

    result = _client(gateway).get_register(_SCRATCH_ID)

    assert result["proband_id"] == _INDIVIDUAL_ID
    call = gateway.calls[0]
    assert call.method == "GET"
    assert call.url == f"{_BASE_URL}/api/pedigrees/{_SCRATCH_ID}/register"
