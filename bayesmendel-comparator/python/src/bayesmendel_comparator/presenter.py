"""Presenters: one per output format.  Each takes (table, sink) and writes."""

from __future__ import annotations

import csv
import json
from typing import Protocol, TextIO

from .comparison_builder import Cell, ComparisonTable
from .config import OutputFormat


class Presenter(Protocol):
    def __call__(self, table: ComparisonTable, sink: TextIO) -> None: ...


def presenter_for(output_format: OutputFormat) -> Presenter:
    """Return the presenter function for a given format choice."""
    return _PRESENTERS[output_format]


# --- Table (aligned, human-readable) --------------------------------------


def present_table(table: ComparisonTable, sink: TextIO) -> None:
    widths = _column_widths(table)
    sink.write(_render_row(table.columns, table.columns, widths) + "\n")
    for row in table.rows:
        cells = tuple(_format_cell(row[col]) for col in table.columns)
        sink.write(_render_row(table.columns, cells, widths) + "\n")


def _column_widths(table: ComparisonTable) -> dict[str, int]:
    widths = {col: len(col) for col in table.columns}
    for row in table.rows:
        for col in table.columns:
            widths[col] = max(widths[col], len(_format_cell(row[col])))
    return widths


def _render_row(
    columns: tuple[str, ...],
    cells: tuple[str, ...],
    widths: dict[str, int],
) -> str:
    return "  ".join(cell.ljust(widths[col]) for col, cell in zip(columns, cells, strict=True))


# --- CSV (RFC 4180) -------------------------------------------------------


def present_csv(table: ComparisonTable, sink: TextIO) -> None:
    # lineterminator="\n" keeps the output platform-independent and friendly
    # to tests reading back via `splitlines()`.
    writer = csv.writer(sink, lineterminator="\n")
    writer.writerow(table.columns)
    for row in table.rows:
        writer.writerow(_format_cell(row[col]) for col in table.columns)


# --- JSON (machine-readable) ----------------------------------------------


def present_json(table: ComparisonTable, sink: TextIO) -> None:
    payload = {
        "columns": list(table.columns),
        "rows": [
            {col: _json_value(row[col]) for col in table.columns} for row in table.rows
        ],
    }
    json.dump(payload, sink, indent=2)
    sink.write("\n")


def _json_value(value: Cell) -> Cell:
    # Keep numeric probabilities as numbers; strings unchanged; None -> null.
    return value


# --- Shared helpers -------------------------------------------------------


def _format_cell(value: Cell) -> str:
    if value is None:
        return "-"
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f"{100 * value:.2f}%"
    return value


_PRESENTERS: dict[OutputFormat, Presenter] = {
    "table": present_table,
    "csv": present_csv,
    "json": present_json,
}
