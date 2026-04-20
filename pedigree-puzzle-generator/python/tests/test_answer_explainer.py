"""Tests for the answer-Markdown generator."""

from __future__ import annotations

import pytest

from pedigree_puzzle.answer_explainer import explain
from pedigree_puzzle.inheritance import Mode
from pedigree_puzzle.puzzle_blueprint import Generations, Size, build_blueprint

_EXPECTED_PHRASES: dict[Mode, tuple[str, ...]] = {
    Mode.AD: (
        "AD",
        "Autosomal Dominant",
        "male-to-male",
    ),
    Mode.AR: (
        "AR",
        "Autosomal Recessive",
        "carriers",
    ),
    Mode.XLR: (
        "XLR",
        "X-linked Recessive",
        "male-to-male",
    ),
    Mode.XLD: (
        "XLD",
        "X-linked Dominant",
        "Every daughter of an affected father",
    ),
    Mode.MT: (
        "MT",
        "Mitochondrial",
        "matrilineal",
    ),
}


@pytest.mark.parametrize("mode", list(Mode))
def test_answer_contains_mode_and_signature_phrases(mode: Mode) -> None:
    blueprint = build_blueprint(mode, Generations.THREE, Size.MEDIUM, 42)
    markdown = explain(blueprint, disease_display_name="Example Condition")
    for phrase in _EXPECTED_PHRASES[mode]:
        assert phrase in markdown, (
            f"Expected phrase {phrase!r} missing from {mode.value} answer"
        )


def test_answer_mentions_the_disease_display_name() -> None:
    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.MEDIUM, 1)
    markdown = explain(blueprint, disease_display_name="Huntington's Disease")
    assert "Huntington's Disease" in markdown


def test_answer_is_well_formed_markdown_with_headings() -> None:
    blueprint = build_blueprint(Mode.AR, Generations.THREE, Size.MEDIUM, 1)
    markdown = explain(blueprint, disease_display_name="Cystic Fibrosis")
    assert markdown.startswith("# Answer: AR")
    assert "## Why this mode fits" in markdown
    assert "## Teaching note" in markdown
