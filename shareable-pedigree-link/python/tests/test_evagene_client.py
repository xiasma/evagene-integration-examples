from typing import Any

import pytest

from shareable_pedigree_link.evagene_client import (
    ApiError,
    CreateApiKeyRequest,
    EvageneClient,
)

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"
_MINTED_KEY_ID = "22222222-2222-2222-2222-222222222222"


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


def _client(gateway: _RecordingGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_parent", http=gateway)


def _happy_response() -> _StubResponse:
    return _StubResponse(
        201,
        {
            "key": "evg_minted_plaintext",
            "api_key": {"id": _MINTED_KEY_ID, "name": "share-12345678-x", "scopes": ["read"]},
        },
    )


def test_create_read_only_api_key_posts_body_with_read_scope_only() -> None:
    gateway = _RecordingGateway(_happy_response())

    minted = _client(gateway).create_read_only_api_key(
        CreateApiKeyRequest(name="share-12345678-x", rate_per_minute=60, rate_per_day=1000),
    )

    assert gateway.last_url == "https://evagene.example/api/auth/me/api-keys"
    assert gateway.last_headers["X-API-Key"] == "evg_parent"
    assert gateway.last_body == {
        "name": "share-12345678-x",
        "scopes": ["read"],
        "rate_limit_per_minute": 60,
        "rate_limit_per_day": 1000,
    }
    assert minted.id == _MINTED_KEY_ID
    assert minted.plaintext_key == "evg_minted_plaintext"


def test_raises_api_error_on_non_2xx() -> None:
    gateway = _RecordingGateway(_StubResponse(403, {}))

    with pytest.raises(ApiError):
        _client(gateway).create_read_only_api_key(
            CreateApiKeyRequest(name="x", rate_per_minute=60, rate_per_day=1000),
        )


def test_raises_api_error_when_plaintext_key_missing() -> None:
    gateway = _RecordingGateway(_StubResponse(201, {"api_key": {"id": _MINTED_KEY_ID}}))

    with pytest.raises(ApiError):
        _client(gateway).create_read_only_api_key(
            CreateApiKeyRequest(name="x", rate_per_minute=60, rate_per_day=1000),
        )


def test_build_embed_url_composes_path_and_encodes_api_key() -> None:
    gateway = _RecordingGateway(_happy_response())

    url = _client(gateway).build_embed_url(_PEDIGREE_ID, "evg_with+special/chars")

    assert url == (
        f"https://evagene.example/api/embed/{_PEDIGREE_ID}?api_key=evg_with%2Bspecial%2Fchars"
    )
