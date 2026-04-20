"""Compose the answer-key Markdown for a given mode and blueprint.

Pure: given a :class:`PedigreeBlueprint` produce the educational
paragraph.  All teaching content flows from :mod:`mode_heuristics` --
this module only arranges it.
"""

from __future__ import annotations

from .inheritance import Mode, Sex
from .mode_heuristics import teaching_cues
from .puzzle_blueprint import PedigreeBlueprint


def explain(blueprint: PedigreeBlueprint, disease_display_name: str) -> str:
    """Return the Markdown body of ``answer.md`` for this puzzle."""
    mode = blueprint.mode
    cues = teaching_cues(mode)
    observations = _observations(blueprint)
    return "\n".join(
        [
            f"# Answer: {mode.value} ({mode.full_name})",
            "",
            f"**Disease in this puzzle:** {disease_display_name}",
            "",
            "## Why this mode fits",
            "",
            *(f"- {cue}" for cue in cues),
            "",
            "## What to look for in this particular pedigree",
            "",
            *(f"- {line}" for line in observations),
            "",
            "## Teaching note",
            "",
            _teaching_note(mode),
            "",
        ]
    )


def _observations(blueprint: PedigreeBlueprint) -> list[str]:
    affected = [ind for ind in blueprint.individuals if ind.affected]
    generations_with_affected = sorted({ind.generation for ind in affected})
    affected_males = sum(1 for ind in affected if ind.sex is Sex.MALE)
    affected_females = len(affected) - affected_males
    return [
        f"{len(affected)} affected individual(s) across generations "
        f"{generations_with_affected or '[none]'}.",
        f"Affected males: {affected_males}; affected females: {affected_females}.",
        f"The proband ({blueprint.proband_id}) is the suggested index case.",
    ]


_TEACHING_NOTES: dict[Mode, str] = {
    Mode.AD: (
        "Textbook heuristic: 'vertical transmission plus male-to-male transmission implies "
        "autosomal dominant.' If you see an affected son of an affected father, X-linked "
        "modes are ruled out."
    ),
    Mode.AR: (
        "Textbook heuristic: 'unaffected parents, affected children -- think recessive.' "
        "If both sexes are affected equally and the pattern clusters within a sibship, "
        "autosomal recessive is the most parsimonious explanation."
    ),
    Mode.XLR: (
        "Textbook heuristic: 'males affected across generations through unaffected females "
        "-- carrier mothers.' No male-to-male transmission is the single strongest "
        "discriminator from autosomal dominant."
    ),
    Mode.XLD: (
        "Textbook heuristic: 'every daughter of an affected father is affected; no son is.' "
        "That asymmetric pattern distinguishes XLD from AD -- AD would affect sons and "
        "daughters in equal proportion."
    ),
    Mode.MT: (
        "Textbook heuristic: 'affected mother -> all children at risk; affected father -> "
        "no children at risk.' Strict matrilineal transmission rules out every nuclear "
        "inheritance mode."
    ),
}


def _teaching_note(mode: Mode) -> str:
    return _TEACHING_NOTES[mode]
