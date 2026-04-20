from __future__ import annotations

import pytest

from tumour_board_briefing.boilerplate import (
    FOOTER_CAVEAT,
    GENERAL_CAVEATS,
    GLOBAL_MODEL_CAVEATS,
    caveats_for,
    caveats_for_models,
)


@pytest.mark.parametrize(
    ("model", "needle"),
    [
        ("CLAUS", "CASH"),
        ("COUCH", "Couch et al. 1997"),
        ("FRANK", "Frank"),
        ("MANCHESTER", "Manchester Scoring System"),
        ("NICE", "NICE CG164 / NG101"),
        ("TYRER_CUZICK", "IBIS-style approximation"),
    ],
)
def test_each_model_caveat_is_present(model: str, needle: str) -> None:
    caveats = caveats_for(model)

    assert caveats, f"no caveats registered for {model}"
    assert any(needle in sentence for sentence in caveats)


def test_unknown_model_yields_no_caveats() -> None:
    assert caveats_for("UNKNOWN") == ()


def test_caveats_for_models_appends_global_boadicea_notice() -> None:
    result = caveats_for_models(("NICE",))

    assert result[-len(GLOBAL_MODEL_CAVEATS) :] == GLOBAL_MODEL_CAVEATS
    assert any("BOADICEA" in sentence for sentence in result)


def test_footer_caveat_contains_clinical_governance_phrase() -> None:
    assert "clinical governance" in FOOTER_CAVEAT
    assert "Not a validated clinical tool" in FOOTER_CAVEAT


def test_general_caveats_mention_governance() -> None:
    assert any("Clinical governance" in sentence for sentence in GENERAL_CAVEATS)


def test_manchester_caveat_quotes_10_and_20_percent_thresholds() -> None:
    [sentence] = caveats_for("MANCHESTER")
    assert "10%" in sentence
    assert "20%" in sentence
