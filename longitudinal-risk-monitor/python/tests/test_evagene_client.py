import random
from typing import Any

import pytest

from longitudinal_risk_monitor.evagene_client import ApiError, EvageneClient

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"


class _StubResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _RecordingGet:
    def __init__(self, responses: list[_StubResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.last_url: str = ""
        self.last_headers: dict[str, str] = {}

    def get_json(self, url: str, *, headers: dict[str, str]) -> _StubResponse:
        self.calls += 1
        self.last_url = url
        self.last_headers = headers
        return self._responses.pop(0)


class _RecordingPost:
    def __init__(self, responses: list[_StubResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.last_url: str = ""
        self.last_body: dict[str, Any] = {}

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> _StubResponse:
        del headers
        self.calls += 1
        self.last_url = url
        self.last_body = body
        return self._responses.pop(0)


def _client(
    get: _RecordingGet | None = None,
    post: _RecordingPost | None = None,
    sleeps: list[float] | None = None,
) -> EvageneClient:
    return EvageneClient(
        base_url="https://evagene.example",
        api_key="evg_test",
        http_get=get or _RecordingGet([_StubResponse(200, [])]),
        http_post=post or _RecordingPost([_StubResponse(200, {})]),
        sleep=(sleeps.append if sleeps is not None else (lambda _: None)),
        rng=random.Random(0),
    )


def test_list_pedigrees_parses_summary_fields() -> None:
    get = _RecordingGet(
        [
            _StubResponse(
                200,
                [
                    {"id": _PEDIGREE_ID, "display_name": "Ashton family"},
                    {"id": "22222222-2222-2222-2222-222222222222", "display_name": ""},
                ],
            ),
        ],
    )

    summaries = _client(get=get).list_pedigrees()

    assert get.last_url == "https://evagene.example/api/pedigrees"
    assert get.last_headers["X-API-Key"] == "evg_test"
    assert [s.display_name for s in summaries] == ["Ashton family", ""]


def test_calculate_nice_sends_model_body() -> None:
    post = _RecordingPost([_StubResponse(200, {"cancer_risk": {}})])

    _client(post=post).calculate_nice(_PEDIGREE_ID)

    assert (
        post.last_url
        == f"https://evagene.example/api/pedigrees/{_PEDIGREE_ID}/risk/calculate"
    )
    assert post.last_body == {"model": "NICE"}


def test_429_triggers_retry_then_success() -> None:
    post = _RecordingPost(
        [_StubResponse(429, {}), _StubResponse(429, {}), _StubResponse(200, {"cancer_risk": {}})],
    )
    sleeps: list[float] = []

    payload = _client(post=post, sleeps=sleeps).calculate_nice(_PEDIGREE_ID)

    assert payload == {"cancer_risk": {}}
    assert post.calls == 3
    assert len(sleeps) == 2
    assert all(delay > 0 for delay in sleeps)
    assert sleeps[1] > sleeps[0]  # exponential growth


def test_429_after_max_retries_raises_api_error() -> None:
    post = _RecordingPost([_StubResponse(429, {})] * 4)

    with pytest.raises(ApiError, match="429"):
        _client(post=post).calculate_nice(_PEDIGREE_ID)


def test_non_2xx_raises_api_error() -> None:
    post = _RecordingPost([_StubResponse(500, {})])

    with pytest.raises(ApiError, match="500"):
        _client(post=post).calculate_nice(_PEDIGREE_ID)
