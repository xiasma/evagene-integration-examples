from nice_traffic_light.classifier import NiceOutcome, RiskCategory
from nice_traffic_light.traffic_light import TrafficLight, to_traffic_light


def _outcome(category: RiskCategory) -> NiceOutcome:
    return NiceOutcome(
        counselee_name="Jane Doe",
        category=category,
        refer_for_genetics_assessment=category is not RiskCategory.NEAR_POPULATION,
        triggers=(),
        notes=(),
    )


def test_near_population_is_green() -> None:
    assert to_traffic_light(_outcome(RiskCategory.NEAR_POPULATION)).colour is TrafficLight.GREEN


def test_moderate_is_amber() -> None:
    assert to_traffic_light(_outcome(RiskCategory.MODERATE)).colour is TrafficLight.AMBER


def test_high_is_red() -> None:
    assert to_traffic_light(_outcome(RiskCategory.HIGH)).colour is TrafficLight.RED


def test_headline_contains_counselee_name() -> None:
    assert "Jane Doe" in to_traffic_light(_outcome(RiskCategory.MODERATE)).headline


def test_headline_falls_back_when_name_absent() -> None:
    outcome = NiceOutcome(
        counselee_name="",
        category=RiskCategory.HIGH,
        refer_for_genetics_assessment=True,
        triggers=(),
        notes=(),
    )
    assert "counselee" in to_traffic_light(outcome).headline
