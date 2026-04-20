"""Teaching heuristics for each inheritance mode, as pure data.

Two callers use this module: :mod:`puzzle_blueprint` reads
:func:`offspring_affected_probability` to decide whether each simulated
child inherits the trait, and :mod:`answer_explainer` reads the
``teaching_cues`` so the answer sheet stays aligned with the same
rules.  Keeping both consumers pointed at one definition prevents drift
between "how we built the puzzle" and "how we explain the answer".
"""

from __future__ import annotations

from dataclasses import dataclass

from .inheritance import Mode, Sex


@dataclass(frozen=True)
class OffspringGenotype:
    """Whether each parent is affected or a silent carrier."""

    mother_affected: bool
    mother_carrier: bool
    father_affected: bool
    father_carrier: bool


def offspring_affected_probability(
    mode: Mode,
    parents: OffspringGenotype,
    child_sex: Sex,
) -> float:
    """Textbook per-offspring affected probability under the given mode.

    Uses the simplest teaching-level rules -- full penetrance, no de
    novo, no anticipation.  That keeps puzzles unambiguous: the student
    is expected to read standard Mendelian cues, not run a risk model.
    """
    rule = _RULE_BY_MODE[mode]
    return rule(parents, child_sex)


def teaching_cues(mode: Mode) -> tuple[str, ...]:
    """Canonical textbook cues a student should notice for each mode."""
    return _TEACHING_CUES[mode]


def _ad(parents: OffspringGenotype, _child_sex: Sex) -> float:
    if parents.mother_affected and parents.father_affected:
        return 1.0
    if parents.mother_affected or parents.father_affected:
        return 0.5
    return 0.0


def _ar(parents: OffspringGenotype, _child_sex: Sex) -> float:
    mother_has_allele = parents.mother_affected or parents.mother_carrier
    father_has_allele = parents.father_affected or parents.father_carrier
    if not (mother_has_allele and father_has_allele):
        return 0.0
    mother_transmits = 1.0 if parents.mother_affected else 0.5
    father_transmits = 1.0 if parents.father_affected else 0.5
    return mother_transmits * father_transmits


def _xlr(parents: OffspringGenotype, child_sex: Sex) -> float:
    # Males affected if their X allele is the disease allele; females
    # need two copies.  Carrier mother + unaffected father is the
    # classic "males affected across generations through females" cue.
    if child_sex is Sex.MALE:
        if parents.mother_affected:
            return 1.0
        if parents.mother_carrier:
            return 0.5
        return 0.0
    # female child
    if parents.father_affected and (parents.mother_affected or parents.mother_carrier):
        return 0.5 if parents.mother_carrier else 1.0
    return 0.0


def _xld(parents: OffspringGenotype, child_sex: Sex) -> float:
    # Under XLD any copy causes disease in males or females; the cue is
    # "affected father -> 100% of daughters, 0% of sons" plus no
    # male-to-male transmission.
    if child_sex is Sex.FEMALE:
        if parents.father_affected:
            return 1.0
        if parents.mother_affected:
            return 0.5
        return 0.0
    # male child: only the X from mother can carry the allele
    if parents.mother_affected:
        return 0.5
    return 0.0


def _mt(parents: OffspringGenotype, _child_sex: Sex) -> float:
    # Mitochondrial: transmitted through the mother to every child.
    # Fathers never transmit.
    if parents.mother_affected:
        return 1.0
    return 0.0


_RULE_BY_MODE = {
    Mode.AD: _ad,
    Mode.AR: _ar,
    Mode.XLR: _xlr,
    Mode.XLD: _xld,
    Mode.MT: _mt,
}


_TEACHING_CUES: dict[Mode, tuple[str, ...]] = {
    Mode.AD: (
        "Affected individuals in every generation (vertical transmission).",
        "Both sexes affected roughly equally.",
        "Male-to-male transmission is possible, ruling out X-linked.",
        "Each child of an affected parent has a ~50% risk.",
    ),
    Mode.AR: (
        "Affected individuals often appear in only one generation "
        "(horizontal clustering among siblings).",
        "Both parents of an affected child are typically unaffected obligate carriers.",
        "Both sexes affected equally.",
        "Consanguinity, where shown, raises the prior probability.",
    ),
    Mode.XLR: (
        "Almost only males are affected.",
        "Transmitted through unaffected female carriers (skipped generations on the female line).",
        "No male-to-male transmission -- affected fathers never pass it to sons.",
        "All daughters of an affected father are obligate carriers.",
    ),
    Mode.XLD: (
        "Both sexes affected, but females typically outnumber males (two X chromosomes).",
        "Every daughter of an affected father is affected; "
        "no sons of an affected father are affected.",
        "No male-to-male transmission.",
        "Affected mothers pass it to ~50% of children of either sex.",
    ),
    Mode.MT: (
        "Transmitted exclusively through the mother (matrilineal).",
        "Affected fathers never transmit to any child.",
        "Affected mothers transmit to all children, though expression can vary with heteroplasmy.",
        "Both sexes affected.",
    ),
}
