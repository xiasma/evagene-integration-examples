from dataclasses import dataclass, field
from typing import Any

import pytest

from cascade_letters.evagene_client import (
    CreateTemplateArgs,
    EvageneApiError,
    EvageneClient,
)

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_TEMPLATE_ID = "22222222-2222-2222-2222-222222222222"


@dataclass
class _StubResponse:
    status_code: int
    payload: Any

    def json(self) -> Any:
        return self.payload


@dataclass
class _RecordingGateway:
    response: _StubResponse
    last_method: str = ""
    last_url: str = ""
    last_headers: dict[str, str] = field(default_factory=dict)
    last_body: dict[str, Any] | None = None

    def send(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> _StubResponse:
        self.last_method = method
        self.last_url = url
        self.last_headers = headers
        self.last_body = body
        return self.response


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_fetch_register_gets_expected_url_and_parses_rows() -> None:
    gateway = _RecordingGateway(
        _StubResponse(
            200,
            {
                "proband_id": "p-1",
                "rows": [
                    {
                        "individual_id": "i-1",
                        "display_name": "Sarah",
                        "relationship_to_proband": "Sister",
                    }
                ],
            },
        )
    )

    register = _client(gateway).fetch_register(_PEDIGREE_ID)

    assert gateway.last_method == "GET"
    assert gateway.last_url == (
        f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/register"
    )
    assert gateway.last_headers["X-API-Key"] == "evg_test"
    assert register.proband_id == "p-1"
    assert register.rows[0].display_name == "Sarah"


def test_list_templates_parses_array() -> None:
    gateway = _RecordingGateway(
        _StubResponse(200, [{"id": "t-1", "name": "foo"}, {"id": "t-2", "name": "bar"}])
    )

    templates = _client(gateway).list_templates()

    assert [t.id for t in templates] == ["t-1", "t-2"]


def test_create_template_posts_body_and_parses_created_template() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"id": "t-new", "name": "cascade"}))

    created = _client(gateway).create_template(
        CreateTemplateArgs(
            name="cascade", description="d", user_prompt_template="{{proband_name}}"
        )
    )

    assert created.id == "t-new"
    assert gateway.last_method == "POST"
    assert gateway.last_url == "https://evagene.example/api/templates"
    assert gateway.last_body is not None
    assert gateway.last_body["name"] == "cascade"
    assert gateway.last_body["is_public"] is False


def test_run_template_puts_pedigree_id_in_query_string() -> None:
    gateway = _RecordingGateway(_StubResponse(200, {"text": "Hello world"}))

    text = _client(gateway).run_template(_TEMPLATE_ID, _PEDIGREE_ID)

    assert text == "Hello world"
    assert gateway.last_url == (
        f"https://evagene.example/api/templates/{_TEMPLATE_ID}/run"
        f"?pedigree_id={_PEDIGREE_ID}"
    )


def test_non_2xx_raises_api_error() -> None:
    gateway = _RecordingGateway(_StubResponse(500, {}))

    with pytest.raises(EvageneApiError, match="HTTP 500"):
        _client(gateway).fetch_register(_PEDIGREE_ID)


def test_missing_text_field_in_run_response_raises() -> None:
    gateway = _RecordingGateway(_StubResponse(200, {"status": "ok"}))

    with pytest.raises(EvageneApiError, match="'text'"):
        _client(gateway).run_template(_TEMPLATE_ID, _PEDIGREE_ID)
