"""Write the question and answer Markdown pair into a timestamped folder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .inheritance import Mode
from .puzzle_blueprint import PedigreeBlueprint


@dataclass(frozen=True)
class PuzzleArtefact:
    folder: Path
    question_path: Path
    answer_path: Path


def write_puzzle(
    *,
    output_dir: Path,
    timestamp: datetime,
    blueprint: PedigreeBlueprint,
    disease_display_name: str,
    pedigree_id: str,
    evagene_base_url: str,
    svg: str,
    answer_markdown: str,
) -> PuzzleArtefact:
    """Create ``<output_dir>/puzzle-<timestamp>/`` and drop the three files."""
    folder = output_dir / f"puzzle-{_slug_timestamp(timestamp)}"
    folder.mkdir(parents=True, exist_ok=False)

    svg_path = folder / "pedigree.svg"
    svg_path.write_text(svg, encoding="utf-8")

    question_path = folder / "question.md"
    question_path.write_text(
        _question_markdown(
            blueprint=blueprint,
            pedigree_id=pedigree_id,
            evagene_base_url=evagene_base_url,
            svg_file_name=svg_path.name,
        ),
        encoding="utf-8",
    )

    answer_path = folder / "answer.md"
    answer_path.write_text(answer_markdown, encoding="utf-8")

    # Deliberately unused locals -- returning the artefact paths is
    # how the caller verifies and prints them.
    _ = disease_display_name

    return PuzzleArtefact(
        folder=folder,
        question_path=question_path,
        answer_path=answer_path,
    )


def _slug_timestamp(timestamp: datetime) -> str:
    aware = timestamp.astimezone(UTC) if timestamp.tzinfo else timestamp
    return aware.strftime("%Y%m%d-%H%M%S")


def _question_markdown(
    *,
    blueprint: PedigreeBlueprint,
    pedigree_id: str,
    evagene_base_url: str,
    svg_file_name: str,
) -> str:
    proband = blueprint.individual(blueprint.proband_id)
    return "\n".join(
        [
            "# Pedigree puzzle",
            "",
            f"![Pedigree]({svg_file_name})",
            "",
            f"**Proband:** {proband.display_name} "
            f"({proband.sex.value}, generation {proband.generation}).",
            "",
            f"Explore the pedigree interactively on Evagene: "
            f"[{evagene_base_url}/pedigrees/{pedigree_id}]"
            f"({evagene_base_url}/pedigrees/{pedigree_id}).",
            "",
            f"Download the SVG: [{svg_file_name}]({svg_file_name}).",
            "",
            "## Your task",
            "",
            "Study the pedigree and identify the **most likely** mode of inheritance "
            "of the shaded trait.",
            "",
            "Choose one:",
            "",
            *(f"- {mode.value} ({mode.full_name})" for mode in Mode),
            "",
            "Justify your choice using the features of the pedigree "
            "(which sexes are affected, transmission pattern across generations, "
            "presence of skipped generations, male-to-male transmission, etc.).",
            "",
        ]
    )
