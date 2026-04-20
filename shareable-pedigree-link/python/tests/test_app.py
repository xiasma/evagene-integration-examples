import io
from typing import Any

import pytest

from shareable_pedigree_link.app import EXIT_OK, EXIT_UNAVAILABLE, EXIT_USAGE, Dependencies, run

_PEDIGREE_ID = "a1cfe665-2e95-4386-9eb8-53d46095478a"
_MINTED_KEY_ID = "22222222-2222-2222-2222-222222222222"
_FIXED_EPOCH = 1_713_600_000
_FIXED_ISO = "2024-04-20T07:11:40+00:00"


class _StubClock:
    def now_iso(self) -> str:
        return _FIXED_ISO

    def now_epoch_seconds(self) -> int:
        return _FIXED_EPOCH


class _StubResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _StubGateway:
    def __init__(self, response: _StubResponse) -> None:
        self._response = response
        self.last_body: dict[str, Any] = {}

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> _StubResponse:
        del url, headers
        self.last_body = body
        return self._response


def _ok_response() -> _StubResponse:
    return _StubResponse(
        201,
        {"key": "evg_minted_happy_path", "api_key": {"id": _MINTED_KEY_ID, "scopes": ["read"]}},
    )


def _deps(gateway: _StubGateway) -> Dependencies:
    return Dependencies(gateway=gateway, clock=_StubClock())


def test_happy_path_prints_iframe_and_exits_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVAGENE_API_KEY", "evg_parent")
    stdout, stderr = io.StringIO(), io.StringIO()
    gateway = _StubGateway(_ok_response())

    exit_code = run([_PEDIGREE_ID], stdout, stderr, deps=_deps(gateway))

    assert exit_code == EXIT_OK
    assert f'<iframe src="https://evagene.net/api/embed/{_PEDIGREE_ID}' in stdout.getvalue()
    assert "evg_minted_happy_path" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_default_key_name_uses_timestamp_when_name_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVAGENE_API_KEY", "evg_parent")
    stdout, stderr = io.StringIO(), io.StringIO()
    gateway = _StubGateway(_ok_response())

    run([_PEDIGREE_ID], stdout, stderr, deps=_deps(gateway))

    assert gateway.last_body["name"] == f"share-{_PEDIGREE_ID[:8]}-{_FIXED_EPOCH}"


def test_missing_api_key_exits_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVAGENE_API_KEY", raising=False)
    stdout, stderr = io.StringIO(), io.StringIO()
    gateway = _StubGateway(_ok_response())

    exit_code = run([_PEDIGREE_ID], stdout, stderr, deps=_deps(gateway))

    assert exit_code == EXIT_USAGE
    assert "EVAGENE_API_KEY" in stderr.getvalue()
    assert stdout.getvalue() == ""


def test_api_failure_exits_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAGENE_API_KEY", "evg_parent")
    stdout, stderr = io.StringIO(), io.StringIO()
    gateway = _StubGateway(_StubResponse(500, {}))

    exit_code = run([_PEDIGREE_ID], stdout, stderr, deps=_deps(gateway))

    assert exit_code == EXIT_UNAVAILABLE
    assert "HTTP 500" in stderr.getvalue()
