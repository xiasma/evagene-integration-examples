"""Serialise an anonymised pedigree and its k-anonymity estimate for output.

Deterministic ordering: keys are emitted in a fixed, documented order so
two runs of the tool against the same input produce byte-identical output.
That property matters for diff-based auditing and for the golden-file
tests further down the tree.
"""

from __future__ import annotations

import json
from typing import Any

from .k_anonymity_estimator import KAnonymityEstimate

_INDIVIDUAL_KEY_ORDER = (
    "id",
    "display_name",
    "generation_label",
    "biological_sex",
    "proband",
    "proband_text",
    "events",
    "diseases",
    "properties",
)
_EVENT_KEY_ORDER = ("type", "date_start", "date_end", "properties")
_DISEASE_KEY_ORDER = ("disease_id", "affection_status", "manifestations")
_RELATIONSHIP_KEY_ORDER = (
    "id",
    "members",
    "consanguinity",
    "consanguinity_override",
    "properties",
)
_EGG_KEY_ORDER = (
    "id",
    "individual_id",
    "individual_ids",
    "relationship_id",
    "adopted",
    "fostered",
)
_TOP_LEVEL_KEY_ORDER = (
    "display_name",
    "date_represented",
    "properties",
    "individuals",
    "relationships",
    "eggs",
    "k_anonymity",
)


def render_json(anonymised: dict[str, Any], estimate: KAnonymityEstimate) -> str:
    """Return a diff-friendly JSON string for ``anonymised`` + ``estimate``."""
    document = {
        "display_name": anonymised.get("display_name", ""),
        "date_represented": anonymised.get("date_represented"),
        "properties": anonymised.get("properties", {}),
        "individuals": [_ordered(individual, _INDIVIDUAL_KEY_ORDER, _individual_child_order)
                        for individual in anonymised.get("individuals", [])],
        "relationships": [_ordered(relationship, _RELATIONSHIP_KEY_ORDER, lambda k, v: v)
                          for relationship in anonymised.get("relationships", [])],
        "eggs": [_ordered(egg, _EGG_KEY_ORDER, lambda k, v: v)
                 for egg in anonymised.get("eggs", [])],
        "k_anonymity": _render_estimate(estimate),
    }
    ordered = {key: document[key] for key in _TOP_LEVEL_KEY_ORDER if key in document}
    return json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"


def _render_estimate(estimate: KAnonymityEstimate) -> dict[str, Any]:
    return {
        "k": estimate.k,
        "bucket_count": estimate.bucket_count,
        "smallest_bucket_key": list(estimate.smallest_bucket_key)
        if estimate.smallest_bucket_key is not None
        else None,
        "total_individuals": estimate.total_individuals,
    }


def _ordered(
    record: dict[str, Any],
    key_order: tuple[str, ...],
    child_handler: Any,
) -> dict[str, Any]:
    return {
        key: child_handler(key, record[key]) for key in key_order if key in record
    }


def _individual_child_order(key: str, value: Any) -> Any:
    if key == "events" and isinstance(value, list):
        return [_ordered(event, _EVENT_KEY_ORDER, lambda k, v: v) for event in value]
    if key == "diseases" and isinstance(value, list):
        return [_ordered(disease, _DISEASE_KEY_ORDER, lambda k, v: v) for disease in value]
    return value
