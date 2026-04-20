import json
from pathlib import Path
from typing import Any

import pytest

from research_anonymiser.anonymiser import (
    AnonymisationRules,
    anonymise,
    replace_display_names,
    round_age,
    strip_free_text_properties,
    truncate_date_of_birth,
)
from research_anonymiser.config import AgePrecision
from research_anonymiser.generation_assigner import assign_generation_labels

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _source() -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(
        (FIXTURES / "source-pedigree.json").read_text(encoding="utf-8")
    )
    return parsed


# ---- Rule: DOB rounding --------------------------------------------------


def test_year_precision_rounds_to_first_of_year() -> None:
    assert truncate_date_of_birth("1968-09-22", AgePrecision.YEAR) == "1968-01-01"


def test_five_year_precision_rounds_down_to_nearest_five() -> None:
    assert truncate_date_of_birth("1968-09-22", AgePrecision.FIVE_YEAR) == "1965-01-01"


def test_decade_precision_rounds_down_to_nearest_ten() -> None:
    assert truncate_date_of_birth("1968-09-22", AgePrecision.DECADE) == "1960-01-01"


def test_none_date_passes_through() -> None:
    assert truncate_date_of_birth(None, AgePrecision.YEAR) is None


def test_malformed_date_becomes_none() -> None:
    assert truncate_date_of_birth("not-a-date", AgePrecision.YEAR) is None


# ---- Rule: age-at-event rounding -----------------------------------------


@pytest.mark.parametrize(
    ("age", "precision", "expected"),
    [
        (43, AgePrecision.YEAR, 43),
        (43, AgePrecision.FIVE_YEAR, 40),
        (58, AgePrecision.DECADE, 50),
        (9, AgePrecision.DECADE, 0),
    ],
)
def test_round_age(age: int, precision: AgePrecision, expected: int) -> None:
    assert round_age(age, precision) == expected


# ---- Rule: free-text property stripping ----------------------------------


def test_strips_keys_whose_names_contain_note_comment_description() -> None:
    cleaned = strip_free_text_properties(
        {
            "death_status": "dead",
            "clinical_note": "PII leaks here",
            "counsellor_comment": "also here",
            "long_description": "and here",
            "age_at_event": 52,
        }
    )
    assert cleaned == {"death_status": "dead", "age_at_event": 52}


def test_free_text_stripping_is_case_insensitive() -> None:
    cleaned = strip_free_text_properties({"Clinical_NOTE": "redact"})
    assert cleaned == {}


# ---- Rule: display-name replacement --------------------------------------


def test_display_names_are_replaced_with_stable_identifiers() -> None:
    individuals = [
        {"id": "a", "display_name": "Alice"},
        {"id": "b", "display_name": "Bob"},
    ]
    identifiers = {"a": "I-1", "b": "I-2"}

    replaced = replace_display_names(individuals, identifiers)

    assert replaced[0]["display_name"] == "I-1"
    assert replaced[1]["display_name"] == "I-2"


def test_anonymise_assigns_roman_indexed_identifiers_per_generation() -> None:
    source = _source()
    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=AgePrecision.YEAR, keep_sex=True)

    result = anonymise(source, labels, rules)

    display_names = sorted(individual["display_name"] for individual in result["individuals"])
    assert display_names == ["I-1", "I-2", "II-1", "II-2", "II-3", "III-1", "III-2"]


# ---- Full transform ------------------------------------------------------


def test_round_trip_matches_golden_year_precision_fixture() -> None:
    source = _source()
    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=AgePrecision.YEAR, keep_sex=True)

    result = anonymise(source, labels, rules)

    expected_full = json.loads((FIXTURES / "expected-anonymised.json").read_text("utf-8"))
    expected = _without_presenter_metadata(expected_full)
    actual = _normalise_for_comparison(result)
    assert actual["individuals"] == expected["individuals"]
    assert actual["relationships"] == expected["relationships"]
    assert actual["eggs"] == expected["eggs"]


def test_round_trip_matches_golden_decade_precision_fixture() -> None:
    source = _source()
    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=AgePrecision.DECADE, keep_sex=True)

    result = anonymise(source, labels, rules)

    expected_full = json.loads((FIXTURES / "expected-anonymised-decade.json").read_text("utf-8"))
    expected = _without_presenter_metadata(expected_full)
    actual = _normalise_for_comparison(result)
    assert actual["individuals"] == expected["individuals"]


def test_no_source_name_appears_anywhere_in_output() -> None:
    source = _source()
    names = {individual["display_name"] for individual in source["individuals"]}
    family_names = {
        individual["name"]["family"]
        for individual in source["individuals"]
        if isinstance(individual.get("name"), dict)
    }
    given_names = {
        given
        for individual in source["individuals"]
        if isinstance(individual.get("name"), dict)
        for given in individual["name"].get("given", [])
    }

    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=AgePrecision.YEAR, keep_sex=True)
    result = anonymise(source, labels, rules)
    serialised = json.dumps(result)

    for needle in names | family_names | given_names:
        assert needle not in serialised, f"source name {needle!r} leaked into anonymised output"


def test_no_keep_sex_redacts_biological_sex() -> None:
    source = _source()
    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=AgePrecision.YEAR, keep_sex=False)

    result = anonymise(source, labels, rules)

    assert all(individual["biological_sex"] == "unknown" for individual in result["individuals"])


def test_consanguinity_coefficient_is_preserved() -> None:
    source = _source()
    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=AgePrecision.YEAR, keep_sex=True)

    result = anonymise(source, labels, rules)

    parent_relationship = next(r for r in result["relationships"] if r["id"] == "r-parents")
    assert parent_relationship["consanguinity"] == 0.0625


def test_notes_on_individuals_are_stripped() -> None:
    source = _source()
    labels = assign_generation_labels(source)
    rules = AnonymisationRules(age_precision=AgePrecision.YEAR, keep_sex=True)

    result = anonymise(source, labels, rules)

    assert all("notes" not in individual for individual in result["individuals"])


def _normalise_for_comparison(result: dict[str, Any]) -> dict[str, Any]:
    """Drop the AnonymisationRules-only intermediate fields the presenter hides."""
    from research_anonymiser.k_anonymity_estimator import estimate_k_anonymity
    from research_anonymiser.presenter import render_json

    rendered = render_json(result, estimate_k_anonymity(result))
    return _without_presenter_metadata(json.loads(rendered))


def _without_presenter_metadata(rendered: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in rendered.items() if key != "k_anonymity"}
