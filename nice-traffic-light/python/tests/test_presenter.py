import io

from nice_traffic_light.classifier import NiceOutcome, RiskCategory
from nice_traffic_light.presenter import present
from nice_traffic_light.traffic_light import TrafficLight, TrafficLightReport


def _report(triggers: tuple[str, ...]) -> TrafficLightReport:
    return TrafficLightReport(
        colour=TrafficLight.RED,
        headline="High risk for Jane Doe \u2014 refer for genetics assessment.",
        outcome=NiceOutcome(
            counselee_name="Jane Doe",
            category=RiskCategory.HIGH,
            refer_for_genetics_assessment=True,
            triggers=triggers,
            notes=(),
        ),
    )


def test_writes_colour_label_and_headline() -> None:
    sink = io.StringIO()

    present(_report(triggers=()), sink)

    first_line = sink.getvalue().splitlines()[0]
    assert first_line.startswith("RED")
    assert "Jane Doe" in first_line


def test_writes_each_trigger_on_its_own_indented_line() -> None:
    sink = io.StringIO()

    present(_report(triggers=("Trigger A", "Trigger B")), sink)

    lines = sink.getvalue().splitlines()
    assert lines[1] == "  - Trigger A"
    assert lines[2] == "  - Trigger B"


def test_writes_only_headline_when_no_triggers() -> None:
    sink = io.StringIO()

    present(_report(triggers=()), sink)

    assert len(sink.getvalue().splitlines()) == 1
