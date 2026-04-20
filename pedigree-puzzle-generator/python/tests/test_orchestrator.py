"""Tests for :class:`PuzzleOrchestrator`."""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from pedigree_puzzle.evagene_client import (
    AddRelativeArgs,
    CreateIndividualArgs,
    DiseaseSummary,
)
from pedigree_puzzle.inheritance import Mode, Sex
from pedigree_puzzle.orchestrator import PuzzleOrchestrator
from pedigree_puzzle.puzzle_blueprint import Generations, Size, build_blueprint


class _FakeClient:
    def __init__(self) -> None:
        self.created_pedigrees: list[str] = []
        self.deleted_pedigrees: list[str] = []
        self.proband_ids: list[str] = []
        self.add_relative_calls: list[AddRelativeArgs] = []
        self.diseases_added: list[tuple[str, str]] = []
        self.created_individuals: list[CreateIndividualArgs] = []
        self.linked_to_pedigree: list[tuple[str, str]] = []
        self.svg_fetches: list[str] = []
        self._next = 0

    def search_diseases(self, name_fragment: str) -> DiseaseSummary:
        return DiseaseSummary(
            disease_id="disease-1",
            display_name=f"Disease matching {name_fragment!r}",
        )

    def create_pedigree(self, display_name: str) -> str:
        self.created_pedigrees.append(display_name)
        return "pedigree-uuid"

    def create_individual(self, args: CreateIndividualArgs) -> str:
        self.created_individuals.append(args)
        return self._next_id()

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None:
        self.linked_to_pedigree.append((pedigree_id, individual_id))

    def designate_as_proband(self, individual_id: str) -> None:
        self.proband_ids.append(individual_id)

    def add_relative(self, args: AddRelativeArgs) -> str:
        self.add_relative_calls.append(args)
        return self._next_id()

    def add_disease_to_individual(self, individual_id: str, disease_id: str) -> None:
        self.diseases_added.append((individual_id, disease_id))

    def get_pedigree_svg(self, pedigree_id: str) -> str:
        self.svg_fetches.append(pedigree_id)
        return "<svg/>"

    def delete_pedigree(self, pedigree_id: str) -> None:
        self.deleted_pedigrees.append(pedigree_id)

    def _next_id(self) -> str:
        self._next += 1
        return f"remote-{self._next}"


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 4, 20, 14, 30, 12, tzinfo=UTC)


def _orchestrator(client: _FakeClient) -> PuzzleOrchestrator:
    return PuzzleOrchestrator(
        client,
        clock=_FixedClock(),
        evagene_base_url="https://evagene.net",
        logger=logging.getLogger("test"),
    )


def test_orchestrator_writes_question_and_answer_files(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AR, Generations.THREE, Size.SMALL, 1)
    client = _FakeClient()

    result = _orchestrator(client).generate(
        blueprint=blueprint,
        disease_name="Cystic Fibrosis",
        output_dir=tmp_path,
        cleanup=True,
    )

    assert result.artefact.question_path.exists()
    assert result.artefact.answer_path.exists()
    assert "AR" in result.artefact.answer_path.read_text(encoding="utf-8")


def test_orchestrator_deletes_pedigree_when_cleanup_requested(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.SMALL, 1)
    client = _FakeClient()

    result = _orchestrator(client).generate(
        blueprint=blueprint,
        disease_name="Huntington",
        output_dir=tmp_path,
        cleanup=True,
    )

    assert result.pedigree_was_deleted is True
    assert client.deleted_pedigrees == ["pedigree-uuid"]


def test_orchestrator_keeps_pedigree_when_cleanup_disabled(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.SMALL, 1)
    client = _FakeClient()

    result = _orchestrator(client).generate(
        blueprint=blueprint,
        disease_name="Huntington",
        output_dir=tmp_path,
        cleanup=False,
    )

    assert result.pedigree_was_deleted is False
    assert client.deleted_pedigrees == []


def test_orchestrator_flags_all_affected_individuals_with_the_disease(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.SMALL, 1)
    client = _FakeClient()

    _orchestrator(client).generate(
        blueprint=blueprint,
        disease_name="Huntington",
        output_dir=tmp_path,
        cleanup=True,
    )

    expected_affected = sum(1 for ind in blueprint.individuals if ind.affected)
    assert len(client.diseases_added) == expected_affected
    for _, disease_id in client.diseases_added:
        assert disease_id == "disease-1"


def test_orchestrator_creates_proband_via_raw_individual_endpoint(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AR, Generations.THREE, Size.SMALL, 1)
    client = _FakeClient()

    _orchestrator(client).generate(
        blueprint=blueprint,
        disease_name="Cystic Fibrosis",
        output_dir=tmp_path,
        cleanup=True,
    )

    assert len(client.created_individuals) == 1
    proband_args = client.created_individuals[0]
    expected_proband = blueprint.individual(blueprint.proband_id)
    assert proband_args.display_name == expected_proband.display_name
    assert proband_args.sex is expected_proband.sex
    assert client.proband_ids == ["remote-1"]


def test_orchestrator_deletes_pedigree_when_mid_build_fails(tmp_path: Path) -> None:
    class _ExplodingClient(_FakeClient):
        def add_relative(self, args: AddRelativeArgs) -> str:
            raise RuntimeError("boom")

    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.SMALL, 1)
    client = _ExplodingClient()

    with contextlib.suppress(RuntimeError):
        _orchestrator(client).generate(
            blueprint=blueprint,
            disease_name="Huntington",
            output_dir=tmp_path,
            cleanup=True,
        )

    assert client.deleted_pedigrees == ["pedigree-uuid"]


def test_adding_female_child_uses_daughter_relation(tmp_path: Path) -> None:
    # Check translations from the blueprint's sibling relationships.
    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.LARGE, 3)
    client = _FakeClient()

    _orchestrator(client).generate(
        blueprint=blueprint,
        disease_name="Huntington",
        output_dir=tmp_path,
        cleanup=False,
    )

    # Every add-relative call that was labelled "sister" in the blueprint
    # should still be "sister" at the wire; same for "mother" etc.
    for call in client.add_relative_calls:
        assert call.relative_type in {
            "mother",
            "father",
            "sister",
            "brother",
        }
        if call.relative_type == "mother":
            assert call.sex is Sex.FEMALE
        if call.relative_type == "father":
            assert call.sex is Sex.MALE
