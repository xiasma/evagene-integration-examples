import pytest

from family_intake.intake_submission import (
    BiologicalSex,
    IntakeValidationError,
    SiblingRelation,
    parse_intake_submission,
)


def test_minimal_submission_keeps_only_proband() -> None:
    submission = parse_intake_submission({"proband_name": "Emma Smith"})

    assert submission.proband.display_name == "Emma Smith"
    assert submission.proband.biological_sex is BiologicalSex.UNKNOWN
    assert submission.proband.year_of_birth is None
    assert submission.mother is None
    assert submission.father is None
    assert submission.siblings == ()


def test_proband_name_is_required() -> None:
    with pytest.raises(IntakeValidationError):
        parse_intake_submission({})
    with pytest.raises(IntakeValidationError):
        parse_intake_submission({"proband_name": "   "})


def test_parses_proband_sex_and_year() -> None:
    submission = parse_intake_submission(
        {"proband_name": "Emma", "proband_sex": "female", "proband_year": "1985"}
    )
    assert submission.proband.biological_sex is BiologicalSex.FEMALE
    assert submission.proband.year_of_birth == 1985


def test_rejects_unknown_biological_sex() -> None:
    with pytest.raises(IntakeValidationError):
        parse_intake_submission({"proband_name": "Emma", "proband_sex": "robot"})


def test_rejects_out_of_range_year() -> None:
    with pytest.raises(IntakeValidationError):
        parse_intake_submission({"proband_name": "Emma", "proband_year": "1700"})
    with pytest.raises(IntakeValidationError):
        parse_intake_submission({"proband_name": "Emma", "proband_year": "2999"})


def test_mother_included_when_name_present() -> None:
    submission = parse_intake_submission(
        {"proband_name": "Emma", "mother_name": "Grace Smith", "mother_year": "1960"}
    )
    assert submission.mother is not None
    assert submission.mother.display_name == "Grace Smith"
    assert submission.mother.year_of_birth == 1960


def test_mother_skipped_when_name_blank() -> None:
    submission = parse_intake_submission({"proband_name": "Emma", "mother_name": "  "})
    assert submission.mother is None


def test_parses_siblings_and_assigns_sex_from_relation() -> None:
    submission = parse_intake_submission(
        {
            "proband_name": "Emma",
            "sibling_0_name": "Alice",
            "sibling_0_relation": "sister",
            "sibling_0_year": "1988",
            "sibling_1_name": "Bob",
            "sibling_1_relation": "half_brother",
        }
    )
    assert len(submission.siblings) == 2
    alice, bob = submission.siblings
    assert alice.display_name == "Alice"
    assert alice.relation is SiblingRelation.SISTER
    assert alice.biological_sex is BiologicalSex.FEMALE
    assert alice.year_of_birth == 1988
    assert bob.biological_sex is BiologicalSex.MALE


def test_skips_blank_sibling_rows() -> None:
    submission = parse_intake_submission(
        {
            "proband_name": "Emma",
            "sibling_0_name": "Alice",
            "sibling_0_relation": "sister",
            "sibling_2_name": "Carol",
            "sibling_2_relation": "sister",
        }
    )
    assert len(submission.siblings) == 2
    assert submission.siblings[0].display_name == "Alice"
    assert submission.siblings[1].display_name == "Carol"


def test_sibling_without_relation_rejects() -> None:
    with pytest.raises(IntakeValidationError):
        parse_intake_submission(
            {
                "proband_name": "Emma",
                "sibling_0_name": "Alice",
                "sibling_0_relation": "",
            }
        )
