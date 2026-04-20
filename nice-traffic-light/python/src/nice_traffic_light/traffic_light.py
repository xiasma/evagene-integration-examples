"""Map a :class:`NiceOutcome` to a :class:`TrafficLightReport`."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .classifier import NiceOutcome, RiskCategory


class TrafficLight(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


@dataclass(frozen=True)
class TrafficLightReport:
    colour: TrafficLight
    headline: str
    outcome: NiceOutcome


_COLOUR_BY_CATEGORY: dict[RiskCategory, TrafficLight] = {
    RiskCategory.NEAR_POPULATION: TrafficLight.GREEN,
    RiskCategory.MODERATE: TrafficLight.AMBER,
    RiskCategory.HIGH: TrafficLight.RED,
}

_HEADLINE_BY_CATEGORY: dict[RiskCategory, str] = {
    RiskCategory.NEAR_POPULATION: (
        "Near-population risk for {name} \u2014 no enhanced surveillance required."
    ),
    RiskCategory.MODERATE: ("Moderate risk for {name} \u2014 refer if further history emerges."),
    RiskCategory.HIGH: ("High risk for {name} \u2014 refer for genetics assessment."),
}


def to_traffic_light(outcome: NiceOutcome) -> TrafficLightReport:
    name = outcome.counselee_name or "counselee"
    return TrafficLightReport(
        colour=_COLOUR_BY_CATEGORY[outcome.category],
        headline=_HEADLINE_BY_CATEGORY[outcome.category].format(name=name),
        outcome=outcome,
    )
