"""Tests for the inheritance-mode rules table."""

from __future__ import annotations

from pedigree_puzzle.inheritance import Mode, Sex
from pedigree_puzzle.mode_heuristics import (
    OffspringGenotype,
    offspring_affected_probability,
    teaching_cues,
)


def _carrier_mother_unaffected_father() -> OffspringGenotype:
    return OffspringGenotype(
        mother_affected=False,
        mother_carrier=True,
        father_affected=False,
        father_carrier=False,
    )


def _both_carriers() -> OffspringGenotype:
    return OffspringGenotype(
        mother_affected=False,
        mother_carrier=True,
        father_affected=False,
        father_carrier=True,
    )


def _affected_mother() -> OffspringGenotype:
    return OffspringGenotype(
        mother_affected=True,
        mother_carrier=False,
        father_affected=False,
        father_carrier=False,
    )


def _affected_father() -> OffspringGenotype:
    return OffspringGenotype(
        mother_affected=False,
        mother_carrier=False,
        father_affected=True,
        father_carrier=False,
    )


def test_ad_affected_parent_50_percent_risk() -> None:
    assert offspring_affected_probability(Mode.AD, _affected_mother(), Sex.MALE) == 0.5
    assert offspring_affected_probability(Mode.AD, _affected_father(), Sex.FEMALE) == 0.5


def test_ad_two_unaffected_parents_zero_risk() -> None:
    unaffected = OffspringGenotype(False, False, False, False)
    assert offspring_affected_probability(Mode.AD, unaffected, Sex.MALE) == 0.0


def test_ar_both_carriers_gives_one_quarter_risk() -> None:
    assert offspring_affected_probability(Mode.AR, _both_carriers(), Sex.MALE) == 0.25


def test_ar_only_one_carrier_parent_zero_risk() -> None:
    parents = _carrier_mother_unaffected_father()
    assert offspring_affected_probability(Mode.AR, parents, Sex.MALE) == 0.0


def test_xlr_carrier_mother_affects_50_percent_of_sons_and_no_daughters() -> None:
    parents = _carrier_mother_unaffected_father()
    assert offspring_affected_probability(Mode.XLR, parents, Sex.MALE) == 0.5
    assert offspring_affected_probability(Mode.XLR, parents, Sex.FEMALE) == 0.0


def test_xld_affected_father_affects_all_daughters_no_sons() -> None:
    parents = _affected_father()
    assert offspring_affected_probability(Mode.XLD, parents, Sex.FEMALE) == 1.0
    assert offspring_affected_probability(Mode.XLD, parents, Sex.MALE) == 0.0


def test_mt_affected_mother_affects_every_child() -> None:
    parents = _affected_mother()
    assert offspring_affected_probability(Mode.MT, parents, Sex.MALE) == 1.0
    assert offspring_affected_probability(Mode.MT, parents, Sex.FEMALE) == 1.0


def test_mt_affected_father_affects_no_child() -> None:
    parents = _affected_father()
    assert offspring_affected_probability(Mode.MT, parents, Sex.MALE) == 0.0
    assert offspring_affected_probability(Mode.MT, parents, Sex.FEMALE) == 0.0


def test_teaching_cues_are_non_empty_for_every_mode() -> None:
    for mode in Mode:
        cues = teaching_cues(mode)
        assert cues, f"No teaching cues for {mode.value}"
        for cue in cues:
            assert cue.strip(), f"Empty teaching cue in {mode.value}"


def test_xlr_teaching_cues_mention_male_to_male_rule() -> None:
    cues = teaching_cues(Mode.XLR)
    joined = " ".join(cues).lower()
    assert "male-to-male" in joined
