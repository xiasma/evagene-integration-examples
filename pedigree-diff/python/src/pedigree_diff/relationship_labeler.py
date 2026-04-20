"""Compute a short relationship-to-proband label for each individual.

This is a *nice to have* for the human-readable formatters.  We keep it
small and conservative: the simple cases (self, parents, siblings,
children, grandparents, aunts/uncles, cousins, spouses) cover most of
the day-to-day cases a clinician reviewing a diff will care about.
Anything we cannot confidently label falls back to ``"relative"``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .snapshot import PedigreeSnapshot


@dataclass(frozen=True)
class FamilyGraph:
    parents_of: dict[str, frozenset[str]]
    children_of: dict[str, frozenset[str]]
    partners_of: dict[str, frozenset[str]]
    sex_of: dict[str, str]


def label_relationship(
    snapshot: PedigreeSnapshot,
    individual_id: str,
) -> str:
    """Short noun phrase describing ``individual_id``'s link to the proband."""
    if snapshot.proband_id is None:
        return "relative"
    if individual_id == snapshot.proband_id:
        return "proband"

    graph = _build_graph(snapshot)
    subject_sex = graph.sex_of.get(individual_id, "")
    context = _LabelContext(
        snapshot=snapshot,
        graph=graph,
        proband=snapshot.proband_id,
        subject_id=individual_id,
        subject_sex=subject_sex,
    )
    for rule in _LABEL_RULES:
        label = rule(context)
        if label is not None:
            return label
    return "relative"


@dataclass(frozen=True)
class _LabelContext:
    snapshot: PedigreeSnapshot
    graph: FamilyGraph
    proband: str
    subject_id: str
    subject_sex: str


def _rule_parent(ctx: _LabelContext) -> str | None:
    if ctx.subject_id in ctx.graph.parents_of.get(ctx.proband, frozenset()):
        return _by_sex(ctx.subject_sex, "father", "mother", "parent")
    return None


def _rule_child(ctx: _LabelContext) -> str | None:
    if ctx.subject_id in ctx.graph.children_of.get(ctx.proband, frozenset()):
        return _by_sex(ctx.subject_sex, "son", "daughter", "child")
    return None


def _rule_partner(ctx: _LabelContext) -> str | None:
    if ctx.subject_id in ctx.graph.partners_of.get(ctx.proband, frozenset()):
        return _by_sex(ctx.subject_sex, "husband", "wife", "partner")
    return None


def _rule_sibling(ctx: _LabelContext) -> str | None:
    if ctx.graph.parents_of.get(ctx.proband, frozenset()) and _shares_any_parent(
        ctx.subject_id,
        ctx.proband,
        ctx.graph,
    ):
        return _by_sex(ctx.subject_sex, "brother", "sister", "sibling")
    return None


def _rule_grandparent(ctx: _LabelContext) -> str | None:
    if ctx.subject_id in _grandparents_of(ctx.proband, ctx.graph):
        side = _parent_side_of(ctx.subject_id, ctx.proband, ctx.graph)
        return _grandparent_label(side, ctx.subject_sex)
    return None


def _rule_great_grandparent(ctx: _LabelContext) -> str | None:
    if ctx.subject_id in _great_grandparents_of(ctx.proband, ctx.graph):
        return _by_sex(
            ctx.subject_sex,
            "great-grandfather",
            "great-grandmother",
            "great-grandparent",
        )
    return None


def _rule_aunt_uncle(ctx: _LabelContext) -> str | None:
    if _is_aunt_or_uncle(ctx.subject_id, ctx.proband, ctx.graph):
        side = _aunt_uncle_side(ctx.subject_id, ctx.proband, ctx.graph)
        return _aunt_uncle_label(side, ctx.subject_sex)
    return None


def _rule_first_cousin(ctx: _LabelContext) -> str | None:
    if _is_first_cousin(ctx.subject_id, ctx.proband, ctx.graph):
        return "first cousin"
    return None


def _rule_niece_nephew(ctx: _LabelContext) -> str | None:
    if _is_niece_or_nephew(ctx.subject_id, ctx.proband, ctx.graph):
        return _by_sex(ctx.subject_sex, "nephew", "niece", "niece/nephew")
    return None


def _rule_grandchild(ctx: _LabelContext) -> str | None:
    if _is_grandchild(ctx.subject_id, ctx.proband, ctx.graph):
        return _by_sex(ctx.subject_sex, "grandson", "granddaughter", "grandchild")
    return None


_LABEL_RULES = (
    _rule_parent,
    _rule_child,
    _rule_partner,
    _rule_sibling,
    _rule_grandparent,
    _rule_great_grandparent,
    _rule_aunt_uncle,
    _rule_first_cousin,
    _rule_niece_nephew,
    _rule_grandchild,
)


def _build_graph(snapshot: PedigreeSnapshot) -> FamilyGraph:
    parents_of: dict[str, set[str]] = defaultdict(set)
    children_of: dict[str, set[str]] = defaultdict(set)
    for pc_link in snapshot.parent_child_links:
        parents_of[pc_link.child_id].add(pc_link.parent_id)
        children_of[pc_link.parent_id].add(pc_link.child_id)

    partners_of: dict[str, set[str]] = defaultdict(set)
    for partner_link in snapshot.partner_links:
        partners_of[partner_link.left].add(partner_link.right)
        partners_of[partner_link.right].add(partner_link.left)

    sex_of = {ind.id: ind.biological_sex for ind in snapshot.individuals}
    return FamilyGraph(
        parents_of={k: frozenset(v) for k, v in parents_of.items()},
        children_of={k: frozenset(v) for k, v in children_of.items()},
        partners_of={k: frozenset(v) for k, v in partners_of.items()},
        sex_of=sex_of,
    )


def _by_sex(sex: str, male: str, female: str, neutral: str) -> str:
    if sex == "male":
        return male
    if sex == "female":
        return female
    return neutral


def _shares_any_parent(a: str, b: str, graph: FamilyGraph) -> bool:
    return bool(
        graph.parents_of.get(a, frozenset()) & graph.parents_of.get(b, frozenset()),
    )


def _grandparents_of(individual_id: str, graph: FamilyGraph) -> frozenset[str]:
    grandparents: set[str] = set()
    for parent in graph.parents_of.get(individual_id, frozenset()):
        grandparents.update(graph.parents_of.get(parent, frozenset()))
    return frozenset(grandparents)


def _great_grandparents_of(individual_id: str, graph: FamilyGraph) -> frozenset[str]:
    great_grandparents: set[str] = set()
    for grandparent in _grandparents_of(individual_id, graph):
        great_grandparents.update(graph.parents_of.get(grandparent, frozenset()))
    return frozenset(great_grandparents)


def _parent_side_of(ancestor_id: str, descendant_id: str, graph: FamilyGraph) -> str:
    """Return ``"maternal"`` / ``"paternal"`` / ``""`` for an ancestor of the proband."""
    for parent_id in graph.parents_of.get(descendant_id, frozenset()):
        if ancestor_id == parent_id or ancestor_id in graph.parents_of.get(
            parent_id,
            frozenset(),
        ):
            return _side_of_parent(graph.sex_of.get(parent_id, ""))
    return ""


def _side_of_parent(parent_sex: str) -> str:
    if parent_sex == "female":
        return "maternal"
    if parent_sex == "male":
        return "paternal"
    return ""


def _grandparent_label(side: str, subject_sex: str) -> str:
    base = _by_sex(subject_sex, "grandfather", "grandmother", "grandparent")
    return f"{side} {base}" if side else base


def _is_aunt_or_uncle(individual_id: str, proband_id: str, graph: FamilyGraph) -> bool:
    proband_parents = graph.parents_of.get(proband_id, frozenset())
    for parent in proband_parents:
        for grandparent in graph.parents_of.get(parent, frozenset()):
            siblings_of_parent = graph.children_of.get(grandparent, frozenset()) - {parent}
            if individual_id in siblings_of_parent:
                return True
    return False


def _aunt_uncle_side(individual_id: str, proband_id: str, graph: FamilyGraph) -> str:
    for parent in graph.parents_of.get(proband_id, frozenset()):
        for grandparent in graph.parents_of.get(parent, frozenset()):
            if individual_id in graph.children_of.get(grandparent, frozenset()) - {parent}:
                return _side_of_parent(graph.sex_of.get(parent, ""))
    return ""


def _aunt_uncle_label(side: str, subject_sex: str) -> str:
    base = _by_sex(subject_sex, "uncle", "aunt", "aunt/uncle")
    return f"{side} {base}" if side else base


def _is_first_cousin(individual_id: str, proband_id: str, graph: FamilyGraph) -> bool:
    proband_parents = graph.parents_of.get(proband_id, frozenset())
    for parent in proband_parents:
        for grandparent in graph.parents_of.get(parent, frozenset()):
            for sibling_of_parent in graph.children_of.get(grandparent, frozenset()) - {parent}:
                if individual_id in graph.children_of.get(sibling_of_parent, frozenset()):
                    return True
    return False


def _is_niece_or_nephew(individual_id: str, proband_id: str, graph: FamilyGraph) -> bool:
    for parent in graph.parents_of.get(proband_id, frozenset()):
        siblings = graph.children_of.get(parent, frozenset()) - {proband_id}
        for sibling in siblings:
            if individual_id in graph.children_of.get(sibling, frozenset()):
                return True
    return False


def _is_grandchild(individual_id: str, proband_id: str, graph: FamilyGraph) -> bool:
    for child in graph.children_of.get(proband_id, frozenset()):
        if individual_id in graph.children_of.get(child, frozenset()):
            return True
    return False


__all__ = ["label_relationship"]
