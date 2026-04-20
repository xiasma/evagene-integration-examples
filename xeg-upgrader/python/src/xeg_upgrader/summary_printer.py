"""Pure renderer for parse-mode responses into a human-readable summary.

Takes the JSON payload the Evagene API returns for
``POST /api/pedigrees/{id}/import/xeg?mode=parse`` and produces counts,
the list of diseases recovered, and any data-level warnings worth
flagging before a clinician commits to the import.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Any

from .config import RunMode

_COUNT_COLUMN_WIDTH = 14


@dataclass(frozen=True)
class ParseSummary:
    filename: str
    individuals: int
    relationships: int
    eggs: int
    diseases: int
    events: int
    disease_names: tuple[str, ...]
    warnings: tuple[str, ...]


def summarise(parse_response: dict[str, Any], filename: str) -> ParseSummary:
    individuals = _array(parse_response, "individuals")
    relationships = _array(parse_response, "relationships")
    eggs = _array(parse_response, "eggs")
    diseases = _array(parse_response, "diseases")

    return ParseSummary(
        filename=filename,
        individuals=len(individuals),
        relationships=len(relationships),
        eggs=len(eggs),
        diseases=len(diseases),
        events=_count_events(individuals) + _count_events(relationships) + _count_events(eggs),
        disease_names=_collect_disease_names(diseases),
        warnings=_detect_warnings(individuals, eggs, diseases),
    )


def render(summary: ParseSummary, mode: RunMode) -> str:
    sink = StringIO()
    sink.write(f"File: {summary.filename}\n")
    sink.write(f"Mode: {_mode_line(mode)}\n\n")
    sink.write("Counts\n")
    _write_count(sink, "individuals", summary.individuals)
    _write_count(sink, "relationships", summary.relationships)
    _write_count(sink, "eggs", summary.eggs)
    _write_count(sink, "diseases", summary.diseases)
    _write_count(sink, "events", summary.events)
    sink.write("\nDiseases\n")
    _write_list(sink, summary.disease_names)
    sink.write("\nWarnings\n")
    _write_list(sink, summary.warnings)
    return sink.getvalue()


def _mode_line(mode: RunMode) -> str:
    if mode is RunMode.PREVIEW:
        return "preview (no pedigree created)"
    return "create (pedigree imported)"


def _write_count(sink: StringIO, label: str, count: int) -> None:
    sink.write(f"  {label.ljust(_COUNT_COLUMN_WIDTH)} {count}\n")


def _write_list(sink: StringIO, items: tuple[str, ...]) -> None:
    if not items:
        sink.write("  (none)\n")
        return
    for item in items:
        sink.write(f"  - {item}\n")


def _array(container: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _count_events(containers: list[dict[str, Any]]) -> int:
    total = 0
    for container in containers:
        events = container.get("events")
        if isinstance(events, list):
            total += len(events)
    return total


def _collect_disease_names(diseases: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(_display_name_of(d) or "(unnamed)" for d in diseases)


def _detect_warnings(
    individuals: list[dict[str, Any]],
    eggs: list[dict[str, Any]],
    diseases: list[dict[str, Any]],
) -> tuple[str, ...]:
    warnings: list[str] = []

    unknown_sex = sum(1 for ind in individuals if _has_no_biological_sex(ind))
    if unknown_sex:
        warnings.append(f"{unknown_sex} individual(s) with unknown biological sex")

    unnamed = sum(1 for ind in individuals if not _display_name_of(ind))
    if unnamed:
        warnings.append(f"{unnamed} individual(s) without a display name")

    orphaned_eggs = sum(1 for egg in eggs if not egg.get("relationship_id"))
    if orphaned_eggs:
        warnings.append(f"{orphaned_eggs} egg(s) with no resolvable parent relationship")

    known_ids = {d.get("id") for d in diseases if isinstance(d.get("id"), str)}
    dangling = sum(
        _count_dangling_manifestations(ind, known_ids) for ind in individuals
    )
    if dangling:
        warnings.append(f"{dangling} disease manifestation(s) with unknown disease_id")

    return tuple(warnings)


def _has_no_biological_sex(individual: dict[str, Any]) -> bool:
    value = individual.get("biological_sex")
    if value is None:
        return True
    return isinstance(value, str) and (not value or value.lower() == "unknown")


def _count_dangling_manifestations(
    individual: dict[str, Any],
    known_ids: set[Any],
) -> int:
    manifestations = individual.get("diseases")
    if not isinstance(manifestations, list):
        return 0
    dangling = 0
    for entry in manifestations:
        if not isinstance(entry, dict):
            continue
        disease_id = entry.get("disease_id")
        if not isinstance(disease_id, str) or disease_id not in known_ids:
            dangling += 1
    return dangling


def _display_name_of(element: dict[str, Any]) -> str:
    value = element.get("display_name")
    return value if isinstance(value, str) else ""
