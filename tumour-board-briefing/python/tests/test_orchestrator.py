from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from tumour_board_briefing.config import load_config
from tumour_board_briefing.evagene_client import ApiError, EvageneClient
from tumour_board_briefing.orchestrator import build_briefing
from tumour_board_briefing.pdf_builder import BriefingDocument

from .fixtures_loader import load_all_risk_fixtures, load_bytes, load_json


@dataclass
class _RecordingSink:
    documents: list[BriefingDocument] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)

    def draw_cover(self, document: BriefingDocument) -> None:
        self.documents.append(document)
        self.calls.append("cover")

    def draw_pedigree_figure(self, document: BriefingDocument) -> None:
        self.calls.append("figure")

    def draw_risk_table(self, document: BriefingDocument) -> None:
        self.calls.append("table")

    def draw_triggers(self, document: BriefingDocument) -> None:
        self.calls.append("triggers")

    def draw_caveats(self, document: BriefingDocument) -> None:
        self.calls.append("caveats")

    def finalise(self) -> None:
        self.calls.append("finalise")


class _FakeGateway:
    def __init__(
        self,
        *,
        detail: dict[str, Any],
        svg: bytes,
        risk_payloads: dict[str, dict[str, Any]],
        fail_models: set[str] | None = None,
    ) -> None:
        self._detail = detail
        self._svg = svg
        self._risk_payloads = risk_payloads
        self._fail_models = fail_models or set()

    def get(self, url: str, *, headers: dict[str, str]) -> Any:
        if url.endswith("/export.svg"):
            return _Response(status_code=200, content=self._svg)
        return _Response(status_code=200, payload=self._detail)

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> Any:
        model = body["model"]
        if model in self._fail_models:
            return _Response(status_code=500, payload={})
        return _Response(status_code=200, payload=self._risk_payloads[model])


@dataclass
class _Response:
    status_code: int = 200
    payload: Any = None
    content: bytes = b""
    text: str = ""

    def json(self) -> Any:
        return self.payload


_PEDIGREE = "11111111-1111-1111-1111-111111111111"
_ENV = {"EVAGENE_API_KEY": "evg_test"}
_TODAY = date(2026, 4, 20)
_NOW = datetime(2026, 4, 20, 9, 30)


def _client(gateway: _FakeGateway) -> EvageneClient:
    return EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway)


def test_end_to_end_builds_document_and_walks_sink() -> None:
    config = load_config([_PEDIGREE], _ENV, today=_TODAY)
    gateway = _FakeGateway(
        detail=load_json("sample-pedigree-detail"),
        svg=load_bytes("sample-pedigree.svg"),
        risk_payloads=load_all_risk_fixtures(),
    )
    sink = _RecordingSink()

    build_briefing(config, _client(gateway), sink, now=lambda: _NOW)

    assert sink.calls == ["cover", "figure", "table", "triggers", "caveats", "finalise"]
    document = sink.documents[0]
    assert document.pedigree_name == "Worked example: BRCA-suspicious family"
    assert document.proband_name == "Jane Example (proband)"
    assert document.generated_at == _NOW
    assert len(document.summaries) == 6
    assert any("IBIS-style approximation" in sentence for sentence in document.caveats)


def test_failed_risk_fetch_degrades_gracefully_into_not_available() -> None:
    config = load_config(
        [_PEDIGREE, "--models", "nice,claus"],
        _ENV,
        today=_TODAY,
    )
    gateway = _FakeGateway(
        detail=load_json("sample-pedigree-detail"),
        svg=load_bytes("sample-pedigree.svg"),
        risk_payloads=load_all_risk_fixtures(),
        fail_models={"CLAUS"},
    )
    sink = _RecordingSink()

    build_briefing(config, _client(gateway), sink, now=lambda: _NOW)

    document = sink.documents[0]
    by_model = {s.model: s for s in document.summaries}
    assert by_model["CLAUS"].headline == "not available"
    assert "High risk" in by_model["NICE"].headline


def test_pedigree_fetch_failure_propagates_as_api_error() -> None:
    class _FailingGateway:
        def get(self, url: str, *, headers: dict[str, str]) -> Any:
            return _Response(status_code=500, payload={})

        def post_json(
            self, url: str, *, headers: dict[str, str], body: dict[str, Any]
        ) -> Any:
            raise AssertionError("should not reach the risk endpoint")

    config = load_config([_PEDIGREE], _ENV, today=_TODAY)
    sink = _RecordingSink()

    try:
        build_briefing(
            config,
            EvageneClient(
                base_url="https://evagene.example",
                api_key="evg_test",
                http=_FailingGateway(),
            ),
            sink,
            now=lambda: _NOW,
        )
    except ApiError:
        assert sink.calls == []
    else:
        raise AssertionError("expected ApiError when the pedigree endpoint fails")
