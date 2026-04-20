"""Persist an :class:`ExtractedFamily` via :class:`EvageneApi`.

Orders calls so every ``relative_of`` points at an already-created
individual: pedigree, proband, parents, then grandparents (per side),
then siblings. No HTTP knowledge of its own.

``affection_status`` and free-text ``notes`` are deliberately not
committed to structured Evagene disease fields -- the call-notes demo
takes the same line, for the same reason: the reviewer should translate
a drawing's shading into a coded disease in the Evagene UI, not a
vision model.
"""

from __future__ import annotations

from dataclasses import dataclass

from .evagene_client import AddRelativeArgs, CreateIndividualArgs, EvageneApi
from .extracted_family import (
    BiologicalSex,
    ExtractedFamily,
    RelativeEntry,
    SiblingEntry,
)


@dataclass(frozen=True)
class WriteResult:
    pedigree_id: str
    proband_id: str
    relatives_added: int


class EvageneWriter:
    def __init__(self, client: EvageneApi) -> None:
        self._client = client

    def write(self, family: ExtractedFamily) -> WriteResult:
        pedigree_id = self._client.create_pedigree(f"{family.proband.display_name}'s family")
        proband_id = self._client.create_individual(
            CreateIndividualArgs(
                display_name=family.proband.display_name,
                biological_sex=family.proband.biological_sex,
                year_of_birth=family.proband.year_of_birth,
            )
        )
        self._client.add_individual_to_pedigree(pedigree_id, proband_id)
        self._client.designate_as_proband(proband_id)

        mother_id = self._maybe_add_relative(
            pedigree_id, proband_id, "mother", BiologicalSex.FEMALE, family.mother
        )
        father_id = self._maybe_add_relative(
            pedigree_id, proband_id, "father", BiologicalSex.MALE, family.father
        )
        relatives_added = _count_added(mother_id, father_id)

        if mother_id is not None:
            relatives_added += self._add_grandparents(
                pedigree_id,
                mother_id,
                family.maternal_grandmother,
                family.maternal_grandfather,
            )
        if father_id is not None:
            relatives_added += self._add_grandparents(
                pedigree_id,
                father_id,
                family.paternal_grandmother,
                family.paternal_grandfather,
            )
        relatives_added += self._add_siblings(pedigree_id, proband_id, family.siblings)

        return WriteResult(
            pedigree_id=pedigree_id,
            proband_id=proband_id,
            relatives_added=relatives_added,
        )

    def _add_grandparents(
        self,
        pedigree_id: str,
        parent_id: str,
        grandmother: RelativeEntry | None,
        grandfather: RelativeEntry | None,
    ) -> int:
        gm_id = self._maybe_add_relative(
            pedigree_id, parent_id, "mother", BiologicalSex.FEMALE, grandmother
        )
        gf_id = self._maybe_add_relative(
            pedigree_id, parent_id, "father", BiologicalSex.MALE, grandfather
        )
        return _count_added(gm_id, gf_id)

    def _add_siblings(
        self,
        pedigree_id: str,
        proband_id: str,
        siblings: tuple[SiblingEntry, ...],
    ) -> int:
        added = 0
        for sibling in siblings:
            self._client.add_relative(
                AddRelativeArgs(
                    pedigree_id=pedigree_id,
                    relative_of=proband_id,
                    relative_type=sibling.relation.value,
                    display_name=sibling.display_name,
                    biological_sex=sibling.biological_sex,
                    year_of_birth=sibling.year_of_birth,
                )
            )
            added += 1
        return added

    def _maybe_add_relative(
        self,
        pedigree_id: str,
        relative_of: str,
        relative_type: str,
        biological_sex: BiologicalSex,
        entry: RelativeEntry | None,
    ) -> str | None:
        if entry is None:
            return None
        return self._client.add_relative(
            AddRelativeArgs(
                pedigree_id=pedigree_id,
                relative_of=relative_of,
                relative_type=relative_type,
                display_name=entry.display_name,
                biological_sex=biological_sex,
                year_of_birth=entry.year_of_birth,
            )
        )


def _count_added(*ids: str | None) -> int:
    return sum(1 for value in ids if value is not None)
