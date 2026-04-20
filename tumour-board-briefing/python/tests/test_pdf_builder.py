from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from tumour_board_briefing.pdf_builder import BriefingDocument, render
from tumour_board_briefing.risk_aggregator import ModelSummary


@dataclass
class _FakeSink:
    """Records every draw call the orchestrator makes, in order."""

    calls: list[str] = field(default_factory=list)

    def draw_cover(self, document: BriefingDocument) -> None:
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


def _document() -> BriefingDocument:
    return BriefingDocument(
        pedigree_id="11111111-1111-1111-1111-111111111111",
        pedigree_name="Worked example",
        proband_name="Jane",
        family_history_summary="Two first-degree relatives affected.",
        generated_at=datetime(2026, 4, 20, 9, 0),
        pedigree_svg=b"<svg/>",
        summaries=(
            ModelSummary(
                model="NICE",
                headline="High risk",
                detail="refer",
                threshold_label="",
                triggers=("Trigger A",),
            ),
        ),
        caveats=("A caveat.",),
        general_caveats=("General caveat.",),
    )


def test_render_walks_sections_in_fixed_order() -> None:
    sink = _FakeSink()

    render(_document(), sink)

    assert sink.calls == ["cover", "figure", "table", "triggers", "caveats", "finalise"]
