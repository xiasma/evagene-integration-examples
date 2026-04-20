"""Orchestration: fetch, aggregate, build document, render.

The orchestrator is a thin seam between the Evagene client, the risk
aggregator, the boilerplate, and the PDF sink. It deliberately does not
talk to reportlab, argparse, or the environment — the composition root
(``app.py``) supplies the dependencies already wired.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from .boilerplate import GENERAL_CAVEATS, caveats_for_models
from .config import Config
from .evagene_client import ApiError, EvageneClient
from .pdf_builder import BriefingDocument, PdfSink, render
from .risk_aggregator import FetchResult, build_summaries


def build_briefing(
    config: Config,
    client: EvageneClient,
    sink: PdfSink,
    *,
    now: Callable[[], datetime],
) -> None:
    """Fetch everything, aggregate, and render the briefing.

    :raises ApiError: the pedigree detail or SVG could not be fetched.
        Individual per-model risk failures are captured into the
        summary rather than aborting the whole briefing — the clinician
        still gets a document that says which models did and did not
        run.
    """
    detail = client.fetch_pedigree_detail(config.pedigree_id)
    svg = client.fetch_pedigree_svg(config.pedigree_id)
    risk_fetches = _fetch_all_models(client, config)

    summaries = build_summaries(risk_fetches)
    caveats = caveats_for_models(config.models)

    document = BriefingDocument(
        pedigree_id=config.pedigree_id,
        pedigree_name=_pedigree_name(detail),
        proband_name=_proband_name(detail, config.counselee_id),
        family_history_summary=_family_history_summary(detail),
        generated_at=now(),
        pedigree_svg=svg,
        summaries=summaries,
        caveats=caveats,
        general_caveats=GENERAL_CAVEATS,
    )
    render(document, sink)


def _fetch_all_models(
    client: EvageneClient,
    config: Config,
) -> dict[str, FetchResult]:
    fetches: dict[str, FetchResult] = {}
    for model in config.models:
        try:
            fetches[model] = client.calculate_risk(
                config.pedigree_id,
                model,
                counselee_id=config.counselee_id,
            )
        except ApiError as error:
            fetches[model] = error
    return fetches


def _pedigree_name(detail: dict[str, Any]) -> str:
    name = detail.get("display_name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "(unnamed pedigree)"


def _proband_name(detail: dict[str, Any], counselee_id: str | None) -> str:
    individuals = detail.get("individuals")
    if not isinstance(individuals, list):
        return "(unknown)"

    if counselee_id is not None:
        for ind in individuals:
            if isinstance(ind, dict) and str(ind.get("id")) == counselee_id:
                return _display_name_of(ind)

    # No counselee override — pick the proband (highest ``proband`` value).
    best_ind: dict[str, Any] | None = None
    best_score = 0.0
    for ind in individuals:
        if not isinstance(ind, dict):
            continue
        score_raw = ind.get("proband", 0.0)
        if isinstance(score_raw, int | float) and not isinstance(score_raw, bool):
            score = float(score_raw)
            if score > best_score:
                best_ind = ind
                best_score = score
    if best_ind is not None:
        return _display_name_of(best_ind)
    return "(no proband designated)"


def _display_name_of(individual: dict[str, Any]) -> str:
    name = individual.get("display_name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "(unnamed individual)"


def _family_history_summary(detail: dict[str, Any]) -> str:
    individuals = detail.get("individuals")
    ind_count = len(individuals) if isinstance(individuals, list) else 0
    relationships = detail.get("relationships")
    rel_count = len(relationships) if isinstance(relationships, list) else 0
    notes = detail.get("notes")
    notes_text = notes.strip() if isinstance(notes, str) and notes.strip() else ""
    base = (
        f"The pedigree contains {ind_count} individual(s) and "
        f"{rel_count} recorded relationship(s)."
    )
    if notes_text:
        return f"{base} Notes: {notes_text}"
    return base
