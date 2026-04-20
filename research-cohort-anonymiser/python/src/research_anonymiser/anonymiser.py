"""Pure transform: PedigreeDetail + Rules -> AnonymisedPedigree.

Every rule lives in a small, named helper so it can be tested in isolation.
The orchestrating ``anonymise`` is a straight-line composition of those
helpers - no branching logic beyond what the rules require.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from .config import AgePrecision

_FREE_TEXT_KEY_FRAGMENTS = ("note", "comment", "description")
_SEX_UNKNOWN = "unknown"
_PEDIGREE_SCRUB_KEYS = ("owner", "owner_name")


@dataclass(frozen=True)
class AnonymisationRules:
    age_precision: AgePrecision
    keep_sex: bool


def anonymise(
    pedigree: dict[str, Any],
    labels: Mapping[str, str],
    rules: AnonymisationRules,
) -> dict[str, Any]:
    """Return a deep-copied, anonymised pedigree dict.

    ``labels`` is a ``{individual_id: generation_label}`` map, typically
    supplied by :func:`~generation_assigner.assign_generation_labels`.
    """
    identifiers = _build_stable_identifiers(labels, pedigree["individuals"])
    result: dict[str, Any] = {
        "display_name": _anonymise_pedigree_display_name(pedigree.get("display_name", "")),
        "date_represented": _truncate_date(
            pedigree.get("date_represented"), rules.age_precision
        ),
        "properties": _strip_free_text_properties(pedigree.get("properties", {})),
        "individuals": [
            _anonymise_individual(individual, identifiers[individual["id"]], rules)
            for individual in pedigree.get("individuals", [])
        ],
        "relationships": [
            _anonymise_relationship(relationship)
            for relationship in pedigree.get("relationships", [])
        ],
        "eggs": [_anonymise_egg(egg) for egg in pedigree.get("eggs", [])],
    }
    for key in _PEDIGREE_SCRUB_KEYS:
        if key in pedigree:
            result[key] = ""
    return result


def replace_display_names(
    individuals: list[dict[str, Any]],
    identifiers: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Exposed for targeted testing of the name-replacement rule."""
    return [
        {**individual, "display_name": identifiers[individual["id"]]}
        for individual in individuals
    ]


def truncate_date_of_birth(raw: str | None, precision: AgePrecision) -> str | None:
    """Exposed for targeted testing of the DOB-rounding rule."""
    return _truncate_date(raw, precision)


def round_age(age: int, precision: AgePrecision) -> int:
    """Exposed for targeted testing of the age-at-event rule."""
    bucket = _bucket_size(precision)
    return (age // bucket) * bucket


def strip_free_text_properties(properties: Mapping[str, Any]) -> dict[str, Any]:
    """Exposed for targeted testing of the free-text rule."""
    return _strip_free_text_properties(properties)


def _build_stable_identifiers(
    labels: Mapping[str, str],
    individuals: list[dict[str, Any]],
) -> dict[str, str]:
    by_label: dict[str, list[str]] = {}
    for individual in individuals:
        individual_id = individual["id"]
        by_label.setdefault(labels[individual_id], []).append(individual_id)
    identifiers: dict[str, str] = {}
    for label, ids in by_label.items():
        for index, individual_id in enumerate(sorted(ids), start=1):
            identifiers[individual_id] = f"{label}-{index}"
    return identifiers


def _anonymise_individual(
    individual: dict[str, Any],
    stable_id: str,
    rules: AnonymisationRules,
) -> dict[str, Any]:
    return {
        "id": individual["id"],
        "display_name": stable_id,
        "biological_sex": _redact_sex(individual.get("biological_sex", ""), rules.keep_sex),
        "generation_label": stable_id.rsplit("-", 1)[0],
        "proband": individual.get("proband", 0),
        "proband_text": "P" if individual.get("proband") else "",
        "events": [_anonymise_event(event, rules.age_precision) for event in _events(individual)],
        "diseases": [_anonymise_disease(disease) for disease in _diseases(individual)],
        "properties": _strip_free_text_properties(individual.get("properties", {})),
    }


def _anonymise_event(event: dict[str, Any], precision: AgePrecision) -> dict[str, Any]:
    return {
        "type": event.get("type", ""),
        "date_start": _truncate_date(event.get("date_start"), precision),
        "date_end": _truncate_date(event.get("date_end"), precision),
        "properties": _round_numeric_ages(
            _strip_free_text_properties(event.get("properties", {})), precision
        ),
    }


def _anonymise_disease(disease: dict[str, Any]) -> dict[str, Any]:
    return {
        "disease_id": disease.get("disease_id", ""),
        "affection_status": disease.get("affection_status", ""),
        "manifestations": [
            _anonymise_manifestation(manifestation)
            for manifestation in disease.get("manifestations") or []
        ],
    }


def _anonymise_manifestation(manifestation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifestation.items()
        if not _is_free_text_key(key) and key != "display_name"
    }


def _anonymise_relationship(relationship: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": relationship.get("id", ""),
        "members": list(relationship.get("members") or []),
        "consanguinity": relationship.get("consanguinity"),
        "consanguinity_override": relationship.get("consanguinity_override", False),
        "properties": _strip_free_text_properties(relationship.get("properties", {})),
    }


def _anonymise_egg(egg: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": egg.get("id", ""),
        "individual_id": egg.get("individual_id"),
        "individual_ids": list(egg.get("individual_ids") or []),
        "relationship_id": egg.get("relationship_id"),
        "adopted": egg.get("adopted", False),
        "fostered": egg.get("fostered", False),
    }


def _anonymise_pedigree_display_name(raw: str) -> str:
    return "Anonymised pedigree" if raw else ""


def _events(individual: dict[str, Any]) -> list[dict[str, Any]]:
    return list(individual.get("events") or [])


def _diseases(individual: dict[str, Any]) -> list[dict[str, Any]]:
    return list(individual.get("diseases") or [])


def _redact_sex(raw: str, keep_sex: bool) -> str:
    return raw if keep_sex else _SEX_UNKNOWN


def _strip_free_text_properties(properties: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in properties.items() if not _is_free_text_key(key)}


def _is_free_text_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _FREE_TEXT_KEY_FRAGMENTS)


def _truncate_date(raw: str | None, precision: AgePrecision) -> str | None:
    if not raw:
        return raw
    try:
        parsed = date.fromisoformat(raw[:10])
    except ValueError:
        return None
    year = parsed.year
    bucket = _bucket_size(precision)
    bucketed_year = (year // bucket) * bucket if bucket > 1 else year
    return f"{bucketed_year:04d}-01-01"


def _round_numeric_ages(
    properties: Mapping[str, Any],
    precision: AgePrecision,
) -> dict[str, Any]:
    rounded: dict[str, Any] = {}
    for key, value in properties.items():
        if "age" in key.lower() and isinstance(value, int) and not isinstance(value, bool):
            rounded[key] = round_age(value, precision)
        else:
            rounded[key] = value
    return rounded


def _bucket_size(precision: AgePrecision) -> int:
    return {
        AgePrecision.YEAR: 1,
        AgePrecision.FIVE_YEAR: 5,
        AgePrecision.DECADE: 10,
    }[precision]
