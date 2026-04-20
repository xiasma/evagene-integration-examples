"""Normalised, immutable value objects describing a pedigree snapshot.

The raw Evagene ``PedigreeDetail`` payload contains much more than this
demo needs.  Reducing to a focused shape early keeps the diff engine a
pure function of two simple inputs and stops schema chatter leaking
into the comparison logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiseaseRecord:
    disease_id: str
    affection_status: str
    age_at_diagnosis: int | None


@dataclass(frozen=True)
class IndividualSnapshot:
    id: str
    display_name: str
    biological_sex: str
    date_of_birth: str | None
    death_status: str
    diseases: tuple[DiseaseRecord, ...]
    is_proband: bool


@dataclass(frozen=True)
class PartnerLink:
    """An unordered pair of individual IDs (sorted for equality)."""

    left: str
    right: str

    @staticmethod
    def of(a: str, b: str) -> PartnerLink:
        low, high = sorted((a, b))
        return PartnerLink(left=low, right=high)


@dataclass(frozen=True)
class ParentChildLink:
    parent_id: str
    child_id: str


@dataclass(frozen=True)
class PedigreeSnapshot:
    pedigree_id: str
    display_name: str
    proband_id: str | None
    individuals: tuple[IndividualSnapshot, ...]
    partner_links: frozenset[PartnerLink]
    parent_child_links: frozenset[ParentChildLink]
