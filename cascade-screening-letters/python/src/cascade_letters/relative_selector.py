"""Pure filter: :class:`RegisterData` in, list of letter targets out.

Selects first-degree (parent / child / sibling) and second-degree
(grandparent / aunt / uncle / nephew / niece / half-sibling) relatives.
Skips the proband, rows with no display name, and more-distant relatives
(great-grandparents, cousins, etc.) — the clinical convention for
cascade screening is the inner two rings.

Relationship labels are produced by Evagene's ``kinship.compute_relationships``;
they may carry a side suffix such as ``"Aunt (maternal)"``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .evagene_client import RegisterData, RegisterRow

_FIRST_DEGREE_BASES: frozenset[str] = frozenset(
    {
        "Father",
        "Mother",
        "Parent",
        "Brother",
        "Sister",
        "Sibling",
        "Son",
        "Daughter",
        "Child",
    }
)

_SECOND_DEGREE_BASES: frozenset[str] = frozenset(
    {
        "Grandfather",
        "Grandmother",
        "Grandparent",
        "Half-brother",
        "Half-sister",
        "Half-sibling",
        "Grandson",
        "Granddaughter",
        "Grandchild",
        "Uncle",
        "Aunt",
        "Uncle/Aunt",
        "Nephew",
        "Niece",
    }
)


@dataclass(frozen=True)
class LetterTarget:
    individual_id: str
    display_name: str
    relationship: str


def select_at_risk_relatives(register: RegisterData) -> list[LetterTarget]:
    return [
        LetterTarget(
            individual_id=row.individual_id,
            display_name=row.display_name,
            relationship=row.relationship_to_proband,
        )
        for row in register.rows
        if _is_letter_target(row, register.proband_id)
    ]


def _is_letter_target(row: RegisterRow, proband_id: str | None) -> bool:
    if row.individual_id == proband_id:
        return False
    if not row.display_name.strip():
        return False
    return _is_first_or_second_degree(row.relationship_to_proband)


def _is_first_or_second_degree(relationship: str) -> bool:
    base = _strip_side_suffix(relationship).strip()
    if not base:
        return False
    if base in _FIRST_DEGREE_BASES:
        return True
    return base in _SECOND_DEGREE_BASES


def _strip_side_suffix(relationship: str) -> str:
    """Drop a trailing ``" (maternal)"`` or ``" (paternal)"`` suffix, if present."""
    for suffix in (" (maternal)", " (paternal)"):
        if relationship.endswith(suffix):
            return relationship[: -len(suffix)]
    return relationship
