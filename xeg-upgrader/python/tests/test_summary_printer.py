from __future__ import annotations

from _fixtures import fixture_json, fixture_text

from xeg_upgrader.config import RunMode
from xeg_upgrader.summary_printer import render, summarise


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip("\n")


def test_simple_pedigree_rendering_matches_expected_snapshot() -> None:
    parsed = fixture_json("sample-simple-parsed.json")
    expected = _normalise(fixture_text("expected-summary.txt"))

    summary = summarise(parsed, "sample-simple.xeg")
    rendered = _normalise(render(summary, RunMode.PREVIEW))

    assert rendered == expected


def test_counts_individuals_relationships_eggs_diseases_and_events() -> None:
    parsed = fixture_json("sample-simple-parsed.json")

    summary = summarise(parsed, "sample-simple.xeg")

    assert summary.individuals == 5
    assert summary.relationships == 2
    assert summary.eggs == 2
    assert summary.diseases == 1
    assert summary.events == 6


def test_flags_individuals_with_unknown_biological_sex() -> None:
    parsed = {
        "individuals": [
            {"display_name": "A", "biological_sex": "female"},
            {"display_name": "B", "biological_sex": "unknown"},
            {"display_name": "C"},
        ],
        "relationships": [],
        "eggs": [],
        "diseases": [],
    }

    summary = summarise(parsed, "x.xeg")

    assert any("unknown biological sex" in w for w in summary.warnings)


def test_flags_eggs_without_a_parent_relationship() -> None:
    parsed = {
        "individuals": [],
        "relationships": [],
        "eggs": [{"individual_id": "abc", "relationship_id": None}],
        "diseases": [],
    }

    summary = summarise(parsed, "x.xeg")

    assert any("no resolvable parent relationship" in w for w in summary.warnings)


def test_flags_manifestations_with_unknown_disease_id() -> None:
    parsed = {
        "individuals": [
            {
                "display_name": "A",
                "biological_sex": "female",
                "diseases": [{"disease_id": "ghost"}],
            }
        ],
        "relationships": [],
        "eggs": [],
        "diseases": [],
    }

    summary = summarise(parsed, "x.xeg")

    assert any("unknown disease_id" in w for w in summary.warnings)


def test_create_mode_renders_as_create_line() -> None:
    parsed = fixture_json("sample-simple-parsed.json")
    summary = summarise(parsed, "x.xeg")

    rendered = render(summary, RunMode.CREATE)

    assert "Mode: create (pedigree imported)" in rendered
