"""End-to-end PDF rendering test.

We feed the orchestrator a fake Evagene gateway, render to a real PDF
in a temp directory, then read the file back with :mod:`pypdf` and
assert that the expected text fragments are present. This is a
golden-file-ish check — it catches regressions in the rendering
pipeline without coupling to exact byte output or page layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pypdf

from tumour_board_briefing.config import load_config
from tumour_board_briefing.evagene_client import EvageneClient
from tumour_board_briefing.orchestrator import build_briefing
from tumour_board_briefing.pdf_builder import ReportLabPdfSink

from .fixtures_loader import load_all_risk_fixtures, load_bytes, load_json, load_text


@dataclass
class _Response:
    status_code: int = 200
    payload: Any = None
    content: bytes = b""
    text: str = ""

    def json(self) -> Any:
        return self.payload


class _FakeGateway:
    def __init__(
        self,
        *,
        detail: dict[str, Any],
        svg: bytes,
        risk_payloads: dict[str, dict[str, Any]],
    ) -> None:
        self._detail = detail
        self._svg = svg
        self._risk_payloads = risk_payloads

    def get(self, url: str, *, headers: dict[str, str]) -> _Response:
        if url.endswith("/export.svg"):
            return _Response(status_code=200, content=self._svg)
        return _Response(status_code=200, payload=self._detail)

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> _Response:
        return _Response(status_code=200, payload=self._risk_payloads[body["model"]])


_PEDIGREE = "11111111-1111-1111-1111-111111111111"


def test_rendered_pdf_contains_expected_phrases(tmp_path: Path) -> None:
    output = tmp_path / "briefing.pdf"
    config = load_config(
        [_PEDIGREE, "--output", str(output)],
        {"EVAGENE_API_KEY": "evg_test"},
        today=date(2026, 4, 20),
    )
    gateway = _FakeGateway(
        detail=load_json("sample-pedigree-detail"),
        svg=load_bytes("sample-pedigree.svg"),
        risk_payloads=load_all_risk_fixtures(),
    )
    sink = ReportLabPdfSink(output)

    build_briefing(
        config,
        EvageneClient(base_url="https://evagene.example", api_key="evg_test", http=gateway),
        sink,
        now=lambda: datetime(2026, 4, 20, 9, 30),
    )

    assert output.exists()
    assert output.stat().st_size > 0

    text = _extract_text(output)
    for fragment in _expected_fragments():
        assert fragment in text, (
            f"expected fragment not found in rendered PDF: {fragment!r}"
        )


def _extract_text(pdf_path: Path) -> str:
    reader = pypdf.PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _expected_fragments() -> list[str]:
    return [line for line in load_text("expected-structure.txt").splitlines() if line.strip()]
