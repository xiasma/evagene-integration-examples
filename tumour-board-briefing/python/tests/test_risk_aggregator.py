from __future__ import annotations

from tumour_board_briefing.risk_aggregator import build_summaries

from .fixtures_loader import load_all_risk_fixtures


def test_build_summaries_covers_all_six_models() -> None:
    fixtures = load_all_risk_fixtures()

    summaries = build_summaries(fixtures)

    models = [s.model for s in summaries]
    assert models == ["CLAUS", "COUCH", "FRANK", "MANCHESTER", "NICE", "TYRER_CUZICK"]


def test_claus_headline_quotes_lifetime_risk() -> None:
    summaries = _by_model(build_summaries(load_all_risk_fixtures()))
    assert "28.8%" in summaries["CLAUS"].headline


def test_couch_headline_quotes_probability_and_flags_threshold() -> None:
    summaries = _by_model(build_summaries(load_all_risk_fixtures()))
    couch = summaries["COUCH"]
    assert "18.5%" in couch.headline
    assert couch.threshold_label == "testing threshold met"


def test_frank_headline_quotes_all_three_probabilities() -> None:
    summaries = _by_model(build_summaries(load_all_risk_fixtures()))
    frank = summaries["FRANK"]
    assert "BRCA1 16.0%" in frank.headline
    assert "BRCA2 9.0%" in frank.headline
    assert "combined 23.6%" in frank.headline


def test_manchester_headline_quotes_scores_and_contributions_become_triggers() -> None:
    summaries = _by_model(build_summaries(load_all_risk_fixtures()))
    manchester = summaries["MANCHESTER"]
    assert "BRCA1 score 13" in manchester.headline
    assert "combined 22" in manchester.headline
    assert "combined >=20%" in manchester.threshold_label
    assert any("ovarian" in trigger for trigger in manchester.triggers)


def test_nice_high_surfaces_category_and_triggers() -> None:
    summaries = _by_model(build_summaries(load_all_risk_fixtures()))
    nice = summaries["NICE"]
    assert "High risk" in nice.headline
    assert nice.detail == "refer for genetics assessment"
    assert "Two or more first-degree relatives with breast cancer <50." in nice.triggers


def test_tyrer_cuzick_headline_quotes_ten_year_and_lifetime() -> None:
    summaries = _by_model(build_summaries(load_all_risk_fixtures()))
    tc = summaries["TYRER_CUZICK"]
    assert "10-year 9.4%" in tc.headline
    assert "lifetime 38.2%" in tc.headline


def test_missing_cancer_risk_block_surfaces_as_not_available() -> None:
    summaries = build_summaries({"NICE": {"model": "NICE"}})
    assert summaries[0].headline == "not available"


def test_fetch_error_surfaces_as_not_available_with_message() -> None:
    summaries = build_summaries({"NICE": RuntimeError("boom")})
    assert summaries[0].headline == "not available"
    assert "boom" in summaries[0].detail


def _by_model(summaries: tuple) -> dict:  # type: ignore[type-arg]
    return {s.model: s for s in summaries}
