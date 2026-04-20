"""PDF rendering for the tumour-board briefing.

The domain model:
- :class:`BriefingDocument` is a value object describing every piece of
  text and the pedigree figure the briefing should contain.
- :class:`PdfSink` is a protocol that records the page-by-page drawing
  intent (cover, figure, table, triggers, caveats). Tests supply a fake
  sink and assert the order of calls.
- :class:`ReportLabPdfSink` is the one production implementation; it
  renders the briefing to an actual PDF using ``reportlab.platypus`` and
  converts the pedigree SVG via ``svglib``.

Keeping rendering behind :class:`PdfSink` means the orchestrator tests
do not depend on reportlab internals (fonts, page metrics, byte output).
"""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

from .boilerplate import FOOTER_CAVEAT
from .risk_aggregator import ModelSummary


@dataclass(frozen=True)
class BriefingDocument:
    pedigree_id: str
    pedigree_name: str
    proband_name: str
    family_history_summary: str
    generated_at: datetime
    pedigree_svg: bytes
    summaries: tuple[ModelSummary, ...]
    caveats: tuple[str, ...]
    general_caveats: tuple[str, ...] = field(default_factory=tuple)


class PdfSink(Protocol):
    def draw_cover(self, document: BriefingDocument) -> None: ...

    def draw_pedigree_figure(self, document: BriefingDocument) -> None: ...

    def draw_risk_table(self, document: BriefingDocument) -> None: ...

    def draw_triggers(self, document: BriefingDocument) -> None: ...

    def draw_caveats(self, document: BriefingDocument) -> None: ...

    def finalise(self) -> None: ...


def render(document: BriefingDocument, sink: PdfSink) -> None:
    """Drive the sink through the six briefing sections in a fixed order."""
    sink.draw_cover(document)
    sink.draw_pedigree_figure(document)
    sink.draw_risk_table(document)
    sink.draw_triggers(document)
    sink.draw_caveats(document)
    sink.finalise()


# ---------------------------------------------------------------------------
# ReportLab-backed sink
# ---------------------------------------------------------------------------

_PAGE_MARGIN = 18 * mm
_TABLE_HEADER = ("Model", "Headline", "Notes", "Threshold")


class ReportLabPdfSink:
    """Accumulates platypus flowables and writes the PDF on ``finalise()``.

    One sink instance writes one PDF file. The sink does not do any work
    until ``finalise()`` is called, so the caller can still abort
    rendering without leaving a half-written file.
    """

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._flowables: list[object] = []
        self._styles = _build_styles()
        self._generated_at: datetime | None = None
        self._pedigree_id: str = ""

    def draw_cover(self, document: BriefingDocument) -> None:
        self._generated_at = document.generated_at
        self._pedigree_id = document.pedigree_id
        self._flowables.extend(_cover_flowables(document, self._styles))

    def draw_pedigree_figure(self, document: BriefingDocument) -> None:
        self._flowables.append(PageBreak())
        self._flowables.append(Paragraph("Pedigree figure", self._styles["H2"]))
        self._flowables.append(Spacer(1, 4 * mm))
        drawing = _render_svg_as_drawing(document.pedigree_svg)
        if drawing is not None:
            self._flowables.append(drawing)
        else:
            self._flowables.append(
                Paragraph(
                    "Pedigree figure unavailable (SVG could not be rendered).",
                    self._styles["Body"],
                ),
            )

    def draw_risk_table(self, document: BriefingDocument) -> None:
        self._flowables.append(PageBreak())
        self._flowables.append(Paragraph("Risk summary", self._styles["H2"]))
        self._flowables.append(Spacer(1, 4 * mm))
        self._flowables.append(_risk_summary_table(document.summaries, self._styles))

    def draw_triggers(self, document: BriefingDocument) -> None:
        self._flowables.append(Spacer(1, 6 * mm))
        self._flowables.append(Paragraph("Triggers and criteria met", self._styles["H2"]))
        self._flowables.append(Spacer(1, 3 * mm))
        self._flowables.extend(_trigger_flowables(document.summaries, self._styles))

    def draw_caveats(self, document: BriefingDocument) -> None:
        self._flowables.append(PageBreak())
        self._flowables.append(Paragraph("Caveats", self._styles["H2"]))
        self._flowables.append(Spacer(1, 3 * mm))
        for sentence in document.general_caveats:
            self._flowables.append(Paragraph(sentence, self._styles["Body"]))
            self._flowables.append(Spacer(1, 2 * mm))
        for sentence in document.caveats:
            self._flowables.append(Paragraph(sentence, self._styles["Body"]))
            self._flowables.append(Spacer(1, 2 * mm))

    def finalise(self) -> None:
        if self._generated_at is None:
            raise RuntimeError(
                "finalise() called before draw_cover(); no content to render."
            )
        footer = _make_footer(self._generated_at, self._pedigree_id)
        doc = _build_doc_template(self._output_path, footer)
        doc.build(self._flowables)


# ---------------------------------------------------------------------------
# Flowable construction helpers (pure: inputs -> platypus flowables)
# ---------------------------------------------------------------------------


def _cover_flowables(
    document: BriefingDocument,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    date_text = document.generated_at.strftime("%d %B %Y")
    return [
        Spacer(1, 20 * mm),
        Paragraph("Tumour-board briefing", styles["H1"]),
        Spacer(1, 6 * mm),
        Paragraph(f"Pedigree: {document.pedigree_name}", styles["H3"]),
        Paragraph(f"Proband: {document.proband_name}", styles["H3"]),
        Paragraph(f"Date: {date_text}", styles["H3"]),
        Spacer(1, 10 * mm),
        Paragraph("Family-history summary", styles["H2"]),
        Spacer(1, 2 * mm),
        Paragraph(document.family_history_summary, styles["Body"]),
    ]


def _risk_summary_table(
    summaries: tuple[ModelSummary, ...],
    styles: dict[str, ParagraphStyle],
) -> Table:
    body_style = styles["BodySmall"]
    rows: list[list[Paragraph]] = [
        [Paragraph(header, styles["TableHeader"]) for header in _TABLE_HEADER]
    ]
    for summary in summaries:
        rows.append(
            [
                Paragraph(summary.model, body_style),
                Paragraph(summary.headline, body_style),
                Paragraph(summary.detail or "-", body_style),
                Paragraph(summary.threshold_label or "-", body_style),
            ]
        )
    table = Table(rows, colWidths=[28 * mm, 60 * mm, 50 * mm, 34 * mm], repeatRows=1)
    table.setStyle(_risk_table_style(len(rows)))
    return table


def _risk_table_style(row_count: int) -> TableStyle:
    commands: list[tuple[object, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
    ]
    for row in range(1, row_count):
        if row % 2 == 0:
            commands.append(
                ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#f0f3f7"))
            )
    return TableStyle(commands)


def _trigger_flowables(
    summaries: tuple[ModelSummary, ...],
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    out: list[object] = []
    any_triggers = False
    for summary in summaries:
        if not summary.triggers:
            continue
        any_triggers = True
        out.append(Paragraph(summary.model, styles["H3"]))
        for trigger in summary.triggers:
            out.append(Paragraph(f"\u2022 {trigger}", styles["Body"]))
        out.append(Spacer(1, 3 * mm))
    if not any_triggers:
        out.append(
            Paragraph(
                "No model-specific triggers or criteria were flagged for this pedigree.",
                styles["Body"],
            ),
        )
    return out


# ---------------------------------------------------------------------------
# Styles / doc template / footer
# ---------------------------------------------------------------------------


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "H1": ParagraphStyle(
            name="TBB_H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
        ),
        "H2": ParagraphStyle(
            name="TBB_H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
        ),
        "H3": ParagraphStyle(
            name="TBB_H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
        ),
        "Body": ParagraphStyle(
            name="TBB_Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
        ),
        "BodySmall": ParagraphStyle(
            name="TBB_BodySmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
        ),
        "TableHeader": ParagraphStyle(
            name="TBB_TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white,
        ),
    }


def _build_doc_template(
    output_path: Path,
    on_page: Callable[[pdfcanvas.Canvas, BaseDocTemplate], None],
) -> BaseDocTemplate:
    frame = Frame(
        _PAGE_MARGIN,
        _PAGE_MARGIN + 10 * mm,
        A4[0] - 2 * _PAGE_MARGIN,
        A4[1] - 2 * _PAGE_MARGIN - 10 * mm,
        id="body",
    )
    doc = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=_PAGE_MARGIN,
        rightMargin=_PAGE_MARGIN,
        topMargin=_PAGE_MARGIN,
        bottomMargin=_PAGE_MARGIN + 10 * mm,
        title="Tumour-board briefing",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    return doc


def _make_footer(
    generated_at: datetime,
    pedigree_id: str,
) -> Callable[[pdfcanvas.Canvas, BaseDocTemplate], None]:
    timestamp = generated_at.strftime("%Y-%m-%d %H:%M")

    def draw(canvas: pdfcanvas.Canvas, _doc: BaseDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#444444"))
        left = _PAGE_MARGIN
        baseline = _PAGE_MARGIN
        canvas.drawString(left, baseline + 4 * mm, f"Generated {timestamp}")
        canvas.drawString(left, baseline, FOOTER_CAVEAT)
        right_text = f"Pedigree {pedigree_id}  page {canvas.getPageNumber()}"
        canvas.drawRightString(A4[0] - _PAGE_MARGIN, baseline, right_text)
        canvas.restoreState()

    return draw


# ---------------------------------------------------------------------------
# SVG -> reportlab Drawing flowable
# ---------------------------------------------------------------------------


def _render_svg_as_drawing(svg_bytes: bytes) -> Flowable | None:
    """Convert an SVG byte string into a reportlab :class:`Drawing`.

    A :class:`Drawing` is itself a :class:`Flowable`, so it can be
    appended directly to the platypus story — no raster conversion
    (and therefore no dependency on an optional Cairo backend) is
    needed. The drawing is scaled in place to fit inside the body frame.

    svglib resolves SVG fonts against the reportlab default ``Helvetica``
    when a referenced face is not available on the host. Text glyphs in
    the embedded figure may therefore not match what the Evagene web UI
    renders; the structural shapes are unaffected.
    """
    try:
        drawing = svg2rlg(io.BytesIO(svg_bytes))
    except Exception:  # pragma: no cover - svglib raises a wide family
        return None
    if not isinstance(drawing, Drawing):
        return None
    _scale_drawing_to_fit(drawing, max_width_mm=170, max_height_mm=200)
    return drawing


def _scale_drawing_to_fit(
    drawing: Drawing,
    *,
    max_width_mm: float,
    max_height_mm: float,
) -> None:
    target_width = max_width_mm * mm
    target_height = max_height_mm * mm
    if drawing.width <= 0 or drawing.height <= 0:
        return
    scale = min(target_width / drawing.width, target_height / drawing.height, 1.0)
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)
