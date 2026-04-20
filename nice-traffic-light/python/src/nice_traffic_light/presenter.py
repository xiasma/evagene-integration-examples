"""Format a :class:`TrafficLightReport` and write it to a text sink."""

from __future__ import annotations

from typing import TextIO

from .traffic_light import TrafficLightReport


def present(report: TrafficLightReport, sink: TextIO) -> None:
    sink.write(f"{report.colour.value:<6} {report.headline}\n")
    for trigger in report.outcome.triggers:
        sink.write(f"  - {trigger}\n")
