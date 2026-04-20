"""Presenters: one per output format. Each takes (rows, sink) and writes."""

from __future__ import annotations

import csv
import json
from typing import Protocol, TextIO

from .config import OutputFormat
from .couple_risk_calculator import CoupleRow

_COLUMNS: tuple[str, ...] = (
    "Disease",
    "Inheritance",
    "CF(A)",
    "CF(B)",
    "API couple risk (A)",
    "API couple risk (B)",
    "Cross-partner offspring risk",
)

# Percentages below this threshold lose resolution at 4 d.p. — switch to scientific.
_SCIENTIFIC_THRESHOLD = 0.0001


class Presenter(Protocol):
    def __call__(self, rows: tuple[CoupleRow, ...], sink: TextIO) -> None: ...


def presenter_for(output_format: OutputFormat) -> Presenter:
    return _PRESENTERS[output_format]


def present_table(rows: tuple[CoupleRow, ...], sink: TextIO) -> None:
    formatted_rows = tuple(_format_row_strings(row) for row in rows)
    widths = _column_widths(formatted_rows)
    sink.write(_render_row(_COLUMNS, widths) + "\n")
    for formatted in formatted_rows:
        sink.write(_render_row(formatted, widths) + "\n")


def present_csv(rows: tuple[CoupleRow, ...], sink: TextIO) -> None:
    writer = csv.writer(sink, lineterminator="\n")
    writer.writerow(_COLUMNS)
    for row in rows:
        writer.writerow(_format_row_strings(row))


def present_json(rows: tuple[CoupleRow, ...], sink: TextIO) -> None:
    payload = {
        "columns": list(_COLUMNS),
        "rows": [_row_to_json(row) for row in rows],
    }
    json.dump(payload, sink, indent=2)
    sink.write("\n")


def _row_to_json(row: CoupleRow) -> dict[str, object]:
    return {
        "Disease": row.disease_name,
        "Inheritance": row.inheritance_pattern,
        "CF(A)": row.carrier_frequency_a,
        "CF(B)": row.carrier_frequency_b,
        "API couple risk (A)": row.api_couple_offspring_risk_a,
        "API couple risk (B)": row.api_couple_offspring_risk_b,
        "Cross-partner offspring risk": row.cross_partner_offspring_risk,
    }


def _format_row_strings(row: CoupleRow) -> tuple[str, ...]:
    return (
        row.disease_name,
        row.inheritance_pattern,
        _format_fraction(row.carrier_frequency_a),
        _format_fraction(row.carrier_frequency_b),
        _format_fraction(row.api_couple_offspring_risk_a),
        _format_fraction(row.api_couple_offspring_risk_b),
        _format_fraction(row.cross_partner_offspring_risk),
    )


def _format_fraction(value: float | None) -> str:
    if value is None:
        return "-"
    if value == 0.0:
        return "0"
    if value < _SCIENTIFIC_THRESHOLD:
        return f"{value:.2e}"
    return f"{value * 100:.4f}%"


def _column_widths(rows: tuple[tuple[str, ...], ...]) -> tuple[int, ...]:
    widths = [len(column) for column in _COLUMNS]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    return tuple(widths)


def _render_row(cells: tuple[str, ...], widths: tuple[int, ...]) -> str:
    return "  ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True))


_PRESENTERS: dict[OutputFormat, Presenter] = {
    "table": present_table,
    "csv": present_csv,
    "json": present_json,
}
