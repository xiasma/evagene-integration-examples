"""Assign a generation label (I, II, III, ...) to every individual in a pedigree.

Pure transform: takes a ``PedigreeDetail`` dict (as returned by
``GET /api/pedigrees/{id}``) and emits ``{individual_id: label}``.

A generation is derived from the pedigree's own eggs + relationships:
each egg points at a relationship (the parental couple) and at one or more
child individual IDs.  We walk from founders (individuals with no parent
link) downwards, assigning ``parent_generation + 1``.  Individuals we can't
place get a stable ``"G?"`` label so the rest of the pipeline can still
reference them.
"""

from __future__ import annotations

from collections import deque
from typing import Any

_UNKNOWN_LABEL = "G?"


def assign_generation_labels(pedigree: dict[str, Any]) -> dict[str, str]:
    """Return a ``{individual_id: label}`` map.

    Labels are roman-numeral strings: ``"I"``, ``"II"``, ``"III"``, ...
    Unknown generation -> ``"G?"``.
    """
    parents_of = _build_parent_map(pedigree)
    partners_of = _build_partner_map(pedigree)
    individual_ids = _collect_individual_ids(pedigree)
    generations = _assign_generations(individual_ids, parents_of)
    _align_partners(generations, partners_of)
    return {
        individual_id: _label_for(generation) for individual_id, generation in generations.items()
    }


def _collect_individual_ids(pedigree: dict[str, Any]) -> list[str]:
    return [
        individual["id"]
        for individual in pedigree.get("individuals", [])
        if isinstance(individual, dict) and isinstance(individual.get("id"), str)
    ]


def _build_partner_map(pedigree: dict[str, Any]) -> dict[str, list[str]]:
    """Return an undirected ``{individual_id: [partner_ids]}`` map.

    A reproductive partnership is expressed by a relationship with >=2
    members.  Each member is a partner of every other member; we capture
    that so we can nudge a founder-sex-partner into the known generation
    of its spouse when the spouse has parents in the pedigree.
    """
    partners: dict[str, list[str]] = {}
    for relationship in pedigree.get("relationships", []):
        if not isinstance(relationship, dict):
            continue
        members = [
            member for member in relationship.get("members") or [] if isinstance(member, str)
        ]
        for individual_id in members:
            partners.setdefault(individual_id, [])
            partners[individual_id].extend(
                other for other in members if other != individual_id
            )
    return partners


def _align_partners(
    generations: dict[str, int | None],
    partners_of: dict[str, list[str]],
) -> None:
    """Promote a founder partner to its spouse's generation when the partner
    would otherwise be labelled as a separate founder (common for in-laws
    with no own-family data in the pedigree).
    """
    changed = True
    while changed:
        changed = False
        for individual_id, current in list(generations.items()):
            partner_generations: list[int] = [
                value
                for partner in partners_of.get(individual_id, [])
                if (value := generations.get(partner)) is not None
            ]
            if not partner_generations:
                continue
            target = max(partner_generations)
            if current is None or target > current:
                generations[individual_id] = target
                changed = True


def _build_parent_map(pedigree: dict[str, Any]) -> dict[str, list[str]]:
    relationships_by_id = {
        relationship["id"]: relationship
        for relationship in pedigree.get("relationships", [])
        if isinstance(relationship, dict) and isinstance(relationship.get("id"), str)
    }
    parents_of: dict[str, list[str]] = {}
    for egg in pedigree.get("eggs", []):
        if not isinstance(egg, dict):
            continue
        children = _children_of_egg(egg)
        parents = _parents_of_egg(egg, relationships_by_id)
        for child in children:
            parents_of.setdefault(child, []).extend(parents)
    return parents_of


def _children_of_egg(egg: dict[str, Any]) -> list[str]:
    single = egg.get("individual_id")
    multiple = egg.get("individual_ids") or []
    if isinstance(multiple, list) and multiple:
        return [child for child in multiple if isinstance(child, str)]
    if isinstance(single, str):
        return [single]
    return []


def _parents_of_egg(
    egg: dict[str, Any],
    relationships_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    relationship_id = egg.get("relationship_id")
    if not isinstance(relationship_id, str):
        return []
    relationship = relationships_by_id.get(relationship_id)
    if relationship is None:
        return []
    members = relationship.get("members") or []
    return [member for member in members if isinstance(member, str)]


def _assign_generations(
    individual_ids: list[str],
    parents_of: dict[str, list[str]],
) -> dict[str, int | None]:
    generations: dict[str, int | None] = dict.fromkeys(individual_ids)
    queue: deque[str] = deque()
    for individual_id in individual_ids:
        if not parents_of.get(individual_id):
            generations[individual_id] = 0
            queue.append(individual_id)

    while queue:
        current = queue.popleft()
        current_generation = generations[current]
        if current_generation is None:
            continue
        for individual_id in individual_ids:
            if current not in parents_of.get(individual_id, []):
                continue
            parent_generations: list[int] = [
                value
                for parent in parents_of[individual_id]
                if (value := generations.get(parent)) is not None
            ]
            if len(parent_generations) != len(parents_of[individual_id]):
                continue
            candidate = max(parent_generations) + 1
            existing = generations[individual_id]
            if existing is None or candidate > existing:
                generations[individual_id] = candidate
                queue.append(individual_id)

    return generations


def _label_for(generation: int | None) -> str:
    if generation is None:
        return _UNKNOWN_LABEL
    return _to_roman(generation + 1)


def _to_roman(number: int) -> str:
    if number <= 0:
        return _UNKNOWN_LABEL
    numerals = (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"),
        (1, "I"),
    )
    remainder = number
    result: list[str] = []
    for value, symbol in numerals:
        while remainder >= value:
            result.append(symbol)
            remainder -= value
    return "".join(result)
