"""Estimate k-anonymity over a simple quasi-identifier bucketing.

We bucket each individual by ``(biological_sex, birth-year bucket,
disease-count)`` -- a deliberately coarse triple that catches the
obvious re-identification footprint while staying honest about its
limits (see the README).  k is the size of the smallest bucket;
k = 1 means at least one individual is uniquely identifiable on the
quasi-identifiers alone.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

_UNKNOWN_YEAR = "unknown"
_YEAR_PREFIX_LENGTH = 4


@dataclass(frozen=True)
class KAnonymityEstimate:
    """Result of a k-anonymity pass over an anonymised pedigree."""

    k: int
    bucket_count: int
    smallest_bucket_key: tuple[str, str, int] | None
    total_individuals: int


def estimate_k_anonymity(anonymised_pedigree: dict[str, Any]) -> KAnonymityEstimate:
    """Compute the quasi-identifier bucket sizes and return the minimum."""
    buckets: Counter[tuple[str, str, int]] = Counter()
    for individual in anonymised_pedigree.get("individuals", []):
        buckets[_bucket_key(individual)] += 1

    if not buckets:
        return KAnonymityEstimate(
            k=0, bucket_count=0, smallest_bucket_key=None, total_individuals=0
        )

    smallest_key, smallest_size = min(buckets.items(), key=lambda item: (item[1], item[0]))
    return KAnonymityEstimate(
        k=smallest_size,
        bucket_count=len(buckets),
        smallest_bucket_key=smallest_key,
        total_individuals=sum(buckets.values()),
    )


def _bucket_key(individual: dict[str, Any]) -> tuple[str, str, int]:
    return (
        _sex_bucket(individual.get("biological_sex", "")),
        _year_bucket(individual.get("events") or []),
        _disease_count(individual.get("diseases") or []),
    )


def _sex_bucket(raw: str) -> str:
    return raw if raw else "unknown"


def _year_bucket(events: list[dict[str, Any]]) -> str:
    for event in events:
        if event.get("type") == "birth":
            date_start = event.get("date_start")
            if isinstance(date_start, str) and len(date_start) >= _YEAR_PREFIX_LENGTH:
                return date_start[:_YEAR_PREFIX_LENGTH]
    return _UNKNOWN_YEAR


def _disease_count(diseases: list[dict[str, Any]]) -> int:
    return sum(1 for disease in diseases if disease.get("affection_status") == "affected")
