import json
from pathlib import Path

import pytest

from nice_traffic_light.classifier import (
    ResponseSchemaError,
    RiskCategory,
    classify_nice_response,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_near_population_parses_to_enum_with_no_triggers() -> None:
    outcome = classify_nice_response(_fixture("near_population"))

    assert outcome.category is RiskCategory.NEAR_POPULATION
    assert outcome.refer_for_genetics_assessment is False
    assert outcome.triggers == ()


def test_moderate_exposes_single_trigger() -> None:
    outcome = classify_nice_response(_fixture("moderate"))

    assert outcome.category is RiskCategory.MODERATE
    assert outcome.refer_for_genetics_assessment is True
    assert len(outcome.triggers) == 1


def test_high_exposes_all_triggers_and_refer_flag() -> None:
    outcome = classify_nice_response(_fixture("high"))

    assert outcome.category is RiskCategory.HIGH
    assert outcome.refer_for_genetics_assessment is True
    assert len(outcome.triggers) == 2


def test_missing_cancer_risk_block_raises() -> None:
    with pytest.raises(ResponseSchemaError):
        classify_nice_response({"model": "NICE"})


def test_unknown_category_raises() -> None:
    with pytest.raises(ResponseSchemaError):
        classify_nice_response(
            {
                "cancer_risk": {
                    "nice_category": "catastrophic",
                    "nice_refer_genetics": True,
                    "nice_triggers": [],
                    "notes": [],
                }
            }
        )


def test_non_string_trigger_raises() -> None:
    with pytest.raises(ResponseSchemaError):
        classify_nice_response(
            {
                "cancer_risk": {
                    "nice_category": "moderate",
                    "nice_refer_genetics": True,
                    "nice_triggers": ["ok", 42],
                    "notes": [],
                }
            }
        )
