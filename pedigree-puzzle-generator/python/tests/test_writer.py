"""Tests for the question/answer file writer."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pedigree_puzzle.inheritance import Mode
from pedigree_puzzle.puzzle_blueprint import Generations, Size, build_blueprint
from pedigree_puzzle.writer import write_puzzle


def test_write_puzzle_creates_timestamped_folder_with_three_files(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AR, Generations.THREE, Size.MEDIUM, 42)
    timestamp = datetime(2026, 4, 20, 14, 30, 12, tzinfo=UTC)

    artefact = write_puzzle(
        output_dir=tmp_path,
        timestamp=timestamp,
        blueprint=blueprint,
        disease_display_name="Cystic Fibrosis",
        pedigree_id="7c8d4d6a-0000-0000-0000-000000000000",
        evagene_base_url="https://evagene.net",
        svg="<svg>...</svg>",
        answer_markdown="# Answer: AR\nsample",
    )

    assert artefact.folder == tmp_path / "puzzle-20260420-143012"
    assert artefact.question_path.name == "question.md"
    assert artefact.answer_path.name == "answer.md"
    assert (artefact.folder / "pedigree.svg").read_text(encoding="utf-8") == "<svg>...</svg>"


def test_question_markdown_links_to_pedigree_on_evagene(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AR, Generations.THREE, Size.MEDIUM, 42)
    timestamp = datetime(2026, 4, 20, 14, 30, 12, tzinfo=UTC)

    artefact = write_puzzle(
        output_dir=tmp_path,
        timestamp=timestamp,
        blueprint=blueprint,
        disease_display_name="Cystic Fibrosis",
        pedigree_id="7c8d4d6a-0000-0000-0000-000000000000",
        evagene_base_url="https://evagene.net",
        svg="<svg/>",
        answer_markdown="# Answer: AR\n",
    )

    question = artefact.question_path.read_text(encoding="utf-8")
    assert "https://evagene.net/pedigrees/7c8d4d6a-0000-0000-0000-000000000000" in question
    assert "![Pedigree](pedigree.svg)" in question
    assert "pedigree.svg" in question


def test_question_and_answer_files_are_written_in_full(tmp_path: Path) -> None:
    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.MEDIUM, 1)
    timestamp = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    artefact = write_puzzle(
        output_dir=tmp_path,
        timestamp=timestamp,
        blueprint=blueprint,
        disease_display_name="Huntington's Disease",
        pedigree_id="00000000-0000-0000-0000-000000000000",
        evagene_base_url="https://evagene.net",
        svg="<svg>hi</svg>",
        answer_markdown="# Answer: AD\nbody",
    )

    assert artefact.answer_path.read_text(encoding="utf-8") == "# Answer: AD\nbody"
    assert "Pedigree puzzle" in artefact.question_path.read_text(encoding="utf-8")
