"""Compose a blueprint into a live pedigree and Markdown artefacts.

No HTTP knowledge -- the orchestrator depends only on the
:class:`EvageneApi` protocol.  No Markdown formatting, either -- that
belongs to :mod:`writer` and :mod:`answer_explainer`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .answer_explainer import explain
from .evagene_client import (
    AddRelativeArgs,
    CreateIndividualArgs,
    EvageneApi,
)
from .puzzle_blueprint import BlueprintIndividual, BuildKind, PedigreeBlueprint
from .writer import PuzzleArtefact, write_puzzle


@dataclass(frozen=True)
class PuzzleResult:
    artefact: PuzzleArtefact
    pedigree_id: str
    pedigree_was_deleted: bool


class Clock(Protocol):
    def now(self) -> datetime: ...


class PuzzleOrchestrator:
    def __init__(
        self,
        client: EvageneApi,
        *,
        clock: Clock,
        evagene_base_url: str,
        logger: logging.Logger,
    ) -> None:
        self._client = client
        self._clock = clock
        self._base_url = evagene_base_url
        self._logger = logger

    def generate(
        self,
        *,
        blueprint: PedigreeBlueprint,
        disease_name: str,
        output_dir: Path,
        cleanup: bool,
    ) -> PuzzleResult:
        disease = self._client.search_diseases(disease_name)
        pedigree_id = self._client.create_pedigree(
            f"Puzzle: {blueprint.mode.value} / {disease.display_name}"
        )
        self._logger.info("Created scratch pedigree %s", pedigree_id)

        try:
            id_map = self._materialise_individuals(blueprint, pedigree_id)
            self._mark_affected(blueprint, id_map, disease.disease_id)
            svg = self._client.get_pedigree_svg(pedigree_id)
            artefact = write_puzzle(
                output_dir=output_dir,
                timestamp=self._clock.now(),
                blueprint=blueprint,
                disease_display_name=disease.display_name,
                pedigree_id=pedigree_id,
                evagene_base_url=self._base_url,
                svg=svg,
                answer_markdown=explain(blueprint, disease.display_name),
            )
        except BaseException:
            self._safely_delete(pedigree_id, reason="aborted mid-build")
            raise

        pedigree_was_deleted = False
        if cleanup:
            self._client.delete_pedigree(pedigree_id)
            pedigree_was_deleted = True
            self._logger.info("Deleted scratch pedigree %s", pedigree_id)

        return PuzzleResult(
            artefact=artefact,
            pedigree_id=pedigree_id,
            pedigree_was_deleted=pedigree_was_deleted,
        )

    def _materialise_individuals(
        self,
        blueprint: PedigreeBlueprint,
        pedigree_id: str,
    ) -> dict[str, str]:
        id_map: dict[str, str] = {}
        for individual in blueprint.individuals:
            id_map[individual.local_id] = self._create_individual(
                individual, pedigree_id, id_map
            )
        id_map_proband = id_map[blueprint.proband_id]
        self._client.designate_as_proband(id_map_proband)
        return id_map

    def _create_individual(
        self,
        individual: BlueprintIndividual,
        pedigree_id: str,
        id_map: dict[str, str],
    ) -> str:
        if individual.build_kind is BuildKind.PROBAND:
            remote = self._client.create_individual(
                CreateIndividualArgs(
                    display_name=individual.display_name,
                    sex=individual.sex,
                )
            )
            self._client.add_individual_to_pedigree(pedigree_id, remote)
            return remote
        relative_of_remote = id_map[individual.relative_of_local_id]
        return self._client.add_relative(
            AddRelativeArgs(
                pedigree_id=pedigree_id,
                relative_of=relative_of_remote,
                relative_type=individual.relative_type,
                display_name=individual.display_name,
                sex=individual.sex,
            )
        )

    def _mark_affected(
        self,
        blueprint: PedigreeBlueprint,
        id_map: dict[str, str],
        disease_id: str,
    ) -> None:
        for individual in blueprint.individuals:
            if not individual.affected:
                continue
            self._client.add_disease_to_individual(
                id_map[individual.local_id], disease_id
            )

    def _safely_delete(self, pedigree_id: str, *, reason: str) -> None:
        try:
            self._client.delete_pedigree(pedigree_id)
            self._logger.info("Deleted scratch pedigree %s (%s)", pedigree_id, reason)
        except Exception:
            self._logger.warning(
                "Failed to delete scratch pedigree %s after %s; clean up manually.",
                pedigree_id,
                reason,
            )
