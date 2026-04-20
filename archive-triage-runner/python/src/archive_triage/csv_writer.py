"""Write a stream of :class:`RowResult` values as CSV to an injected sink."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from typing import TextIO

from .row_result import RowResult

HEADER: tuple[str, ...] = (
    "pedigree_id",
    "proband_name",
    "category",
    "refer_for_genetics",
    "triggers_matched_count",
    "error",
)


class CsvWriter:
    def __init__(self, sink: TextIO) -> None:
        self._writer = csv.writer(sink, lineterminator="\n")

    def write(self, rows: Iterable[RowResult]) -> None:
        self._writer.writerow(HEADER)
        for row in rows:
            self._writer.writerow(_row_values(row))


def _row_values(row: RowResult) -> tuple[str, str, str, str, str, str]:
    return (
        row.pedigree_id,
        row.proband_name,
        row.category,
        _format_bool(row.refer_for_genetics),
        str(row.triggers_matched_count),
        row.error,
    )


def _format_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"
