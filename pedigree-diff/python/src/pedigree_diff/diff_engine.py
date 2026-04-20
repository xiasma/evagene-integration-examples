"""Pure comparison of two :class:`PedigreeSnapshot` values → :class:`Diff`.

No I/O, no clock, no globals.  The output is deterministically ordered
so formatters produce byte-stable output and tests can rely on golden
files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .snapshot import (
    DiseaseRecord,
    IndividualSnapshot,
    ParentChildLink,
    PartnerLink,
    PedigreeSnapshot,
)


class FieldChangeKind(str, Enum):
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    BIOLOGICAL_SEX = "biological_sex"
    DEATH_STATUS = "death_status"


@dataclass(frozen=True)
class FieldChange:
    kind: FieldChangeKind
    before: str
    after: str


@dataclass(frozen=True)
class DiseaseChange:
    disease: DiseaseRecord
    added: bool  # False → removed


@dataclass(frozen=True)
class AddedIndividual:
    individual: IndividualSnapshot


@dataclass(frozen=True)
class RemovedIndividual:
    individual: IndividualSnapshot


@dataclass(frozen=True)
class UpdatedIndividual:
    before: IndividualSnapshot
    after: IndividualSnapshot
    field_changes: tuple[FieldChange, ...]
    disease_changes: tuple[DiseaseChange, ...]


@dataclass(frozen=True)
class UnchangedIndividual:
    individual: IndividualSnapshot


@dataclass(frozen=True)
class PartnerLinkChange:
    link: PartnerLink
    added: bool


@dataclass(frozen=True)
class ParentChildLinkChange:
    link: ParentChildLink
    added: bool


@dataclass(frozen=True)
class ProbandChange:
    before: str | None
    after: str | None


@dataclass(frozen=True)
class Diff:
    added: tuple[AddedIndividual, ...]
    removed: tuple[RemovedIndividual, ...]
    updated: tuple[UpdatedIndividual, ...]
    unchanged: tuple[UnchangedIndividual, ...]
    partner_link_changes: tuple[PartnerLinkChange, ...]
    parent_child_link_changes: tuple[ParentChildLinkChange, ...]
    proband_change: ProbandChange | None

    def has_changes(self) -> bool:
        return bool(
            self.added
            or self.removed
            or self.updated
            or self.partner_link_changes
            or self.parent_child_link_changes
            or self.proband_change,
        )


def diff_pedigrees(before: PedigreeSnapshot, after: PedigreeSnapshot) -> Diff:
    before_by_id = {ind.id: ind for ind in before.individuals}
    after_by_id = {ind.id: ind for ind in after.individuals}

    added = tuple(
        AddedIndividual(individual=after_by_id[i])
        for i in _sorted_by_display_name(after_by_id.keys() - before_by_id.keys(), after_by_id)
    )
    removed = tuple(
        RemovedIndividual(individual=before_by_id[i])
        for i in _sorted_by_display_name(before_by_id.keys() - after_by_id.keys(), before_by_id)
    )

    common_ids = _sorted_by_display_name(
        before_by_id.keys() & after_by_id.keys(),
        after_by_id,
    )
    updated: list[UpdatedIndividual] = []
    unchanged: list[UnchangedIndividual] = []
    for ind_id in common_ids:
        field_changes = _field_changes(before_by_id[ind_id], after_by_id[ind_id])
        disease_changes = _disease_changes(before_by_id[ind_id], after_by_id[ind_id])
        if field_changes or disease_changes:
            updated.append(
                UpdatedIndividual(
                    before=before_by_id[ind_id],
                    after=after_by_id[ind_id],
                    field_changes=field_changes,
                    disease_changes=disease_changes,
                ),
            )
        else:
            unchanged.append(UnchangedIndividual(individual=after_by_id[ind_id]))

    return Diff(
        added=added,
        removed=removed,
        updated=tuple(updated),
        unchanged=tuple(unchanged),
        partner_link_changes=_partner_link_changes(before, after),
        parent_child_link_changes=_parent_child_link_changes(before, after),
        proband_change=_proband_change(before, after),
    )


def _field_changes(
    before: IndividualSnapshot,
    after: IndividualSnapshot,
) -> tuple[FieldChange, ...]:
    candidates: list[FieldChange] = []
    _maybe_append(candidates, FieldChangeKind.NAME, before.display_name, after.display_name)
    _maybe_append(
        candidates,
        FieldChangeKind.DATE_OF_BIRTH,
        before.date_of_birth or "",
        after.date_of_birth or "",
    )
    _maybe_append(
        candidates,
        FieldChangeKind.BIOLOGICAL_SEX,
        before.biological_sex,
        after.biological_sex,
    )
    _maybe_append(
        candidates,
        FieldChangeKind.DEATH_STATUS,
        before.death_status,
        after.death_status,
    )
    return tuple(candidates)


def _maybe_append(
    sink: list[FieldChange],
    kind: FieldChangeKind,
    before: str,
    after: str,
) -> None:
    if before != after:
        sink.append(FieldChange(kind=kind, before=before, after=after))


def _disease_changes(
    before: IndividualSnapshot,
    after: IndividualSnapshot,
) -> tuple[DiseaseChange, ...]:
    before_by_id = {d.disease_id: d for d in before.diseases}
    after_by_id = {d.disease_id: d for d in after.diseases}

    changes: list[DiseaseChange] = []
    for disease_id in sorted(after_by_id.keys() - before_by_id.keys()):
        changes.append(DiseaseChange(disease=after_by_id[disease_id], added=True))
    for disease_id in sorted(before_by_id.keys() - after_by_id.keys()):
        changes.append(DiseaseChange(disease=before_by_id[disease_id], added=False))
    for disease_id in sorted(before_by_id.keys() & after_by_id.keys()):
        if before_by_id[disease_id] != after_by_id[disease_id]:
            changes.append(DiseaseChange(disease=before_by_id[disease_id], added=False))
            changes.append(DiseaseChange(disease=after_by_id[disease_id], added=True))
    return tuple(changes)


def _partner_link_changes(
    before: PedigreeSnapshot,
    after: PedigreeSnapshot,
) -> tuple[PartnerLinkChange, ...]:
    added_links = sorted(after.partner_links - before.partner_links, key=_partner_sort_key)
    removed_links = sorted(before.partner_links - after.partner_links, key=_partner_sort_key)
    changes = [PartnerLinkChange(link=link, added=True) for link in added_links]
    changes += [PartnerLinkChange(link=link, added=False) for link in removed_links]
    return tuple(changes)


def _parent_child_link_changes(
    before: PedigreeSnapshot,
    after: PedigreeSnapshot,
) -> tuple[ParentChildLinkChange, ...]:
    added_links = sorted(
        after.parent_child_links - before.parent_child_links,
        key=_parent_child_sort_key,
    )
    removed_links = sorted(
        before.parent_child_links - after.parent_child_links,
        key=_parent_child_sort_key,
    )
    changes = [ParentChildLinkChange(link=link, added=True) for link in added_links]
    changes += [ParentChildLinkChange(link=link, added=False) for link in removed_links]
    return tuple(changes)


def _proband_change(
    before: PedigreeSnapshot,
    after: PedigreeSnapshot,
) -> ProbandChange | None:
    if before.proband_id == after.proband_id:
        return None
    return ProbandChange(before=before.proband_id, after=after.proband_id)


def _sorted_by_display_name(
    ids: set[str],
    lookup: dict[str, IndividualSnapshot],
) -> list[str]:
    return sorted(ids, key=lambda i: (lookup[i].display_name, lookup[i].id))


def _partner_sort_key(link: PartnerLink) -> tuple[str, str]:
    return (link.left, link.right)


def _parent_child_sort_key(link: ParentChildLink) -> tuple[str, str]:
    return (link.parent_id, link.child_id)
