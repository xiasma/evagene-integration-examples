"""Orchestrates the per-file pipeline and streams :class:`RowResult` values.

Knows nothing about HTTP or the filesystem — delegates to
:class:`EvageneApi` for API calls and receives pre-read ``(path, content)``
pairs from the scanner.  Errors are captured as rows rather than raised
so a single rotten file does not sink the whole archive.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from .evagene_client import EvageneApi, EvageneApiError
from .gedcom_scanner import GedcomFile
from .row_result import RowResult


@dataclass(frozen=True)
class TriageOptions:
    concurrency: int


class TriageService:
    def __init__(self, client: EvageneApi, options: TriageOptions) -> None:
        self._client = client
        self._options = options

    def triage(self, files: Iterable[GedcomFile]) -> Iterator[RowResult]:
        with ThreadPoolExecutor(max_workers=self._options.concurrency) as pool:
            yield from pool.map(self._triage_one, files)

    def _triage_one(self, file: GedcomFile) -> RowResult:
        display_name = file.path.stem
        try:
            pedigree_id = self._client.create_pedigree(display_name)
        except EvageneApiError as error:
            return _failure(
                pedigree_id="",
                proband_name=display_name,
                message=f"create_pedigree failed: {error}",
            )

        try:
            self._client.import_gedcom(pedigree_id, file.content)
        except EvageneApiError as error:
            return _failure(pedigree_id, display_name, f"import_gedcom failed: {error}")

        try:
            if not self._client.has_proband(pedigree_id):
                return _failure(
                    pedigree_id,
                    display_name,
                    "no proband designated in GEDCOM — mark one with a _PROBAND 1 tag.",
                )
        except EvageneApiError as error:
            return _failure(pedigree_id, display_name, f"proband check failed: {error}")

        try:
            payload = self._client.calculate_nice(pedigree_id)
        except EvageneApiError as error:
            return _failure(pedigree_id, display_name, f"calculate_nice failed: {error}")

        return _row_from_payload(pedigree_id, display_name, payload)


def _row_from_payload(
    pedigree_id: str,
    fallback_name: str,
    payload: dict[str, Any],
) -> RowResult:
    cancer_risk = payload.get("cancer_risk")
    proband_name = _string(payload, "counselee_name") or fallback_name
    if not isinstance(cancer_risk, dict):
        return _failure(pedigree_id, proband_name, "NICE response missing cancer_risk block.")

    category = _string(cancer_risk, "nice_category")
    triggers = cancer_risk.get("nice_triggers", [])
    if not category or not isinstance(triggers, list):
        return _failure(pedigree_id, proband_name, "NICE response schema unexpected.")

    return RowResult(
        pedigree_id=pedigree_id,
        proband_name=proband_name,
        category=category,
        refer_for_genetics=_optional_bool(cancer_risk, "nice_refer_genetics"),
        triggers_matched_count=len(triggers),
        error="",
    )


def _failure(pedigree_id: str, proband_name: str, message: str) -> RowResult:
    return RowResult(
        pedigree_id=pedigree_id,
        proband_name=proband_name,
        category="",
        refer_for_genetics=None,
        triggers_matched_count=0,
        error=message,
    )


def _string(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    return value if isinstance(value, str) else ""


def _optional_bool(container: dict[str, Any], key: str) -> bool | None:
    value = container.get(key)
    return value if isinstance(value, bool) else None
