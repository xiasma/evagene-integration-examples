"""Render an :class:`ExtractedFamily` as pretty JSON plus a readable preview."""

from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from typing import Any, TextIO

from .extracted_family import ExtractedFamily, RelativeEntry, SiblingEntry

_RELATIVE_LABELS: list[tuple[str, str]] = [
    ("mother", "mother"),
    ("father", "father"),
    ("maternal_grandmother", "maternal grandmother"),
    ("maternal_grandfather", "maternal grandfather"),
    ("paternal_grandmother", "paternal grandmother"),
    ("paternal_grandfather", "paternal grandfather"),
]


def present(family: ExtractedFamily, sink: TextIO) -> None:
    sink.write(_to_json(family))
    sink.write("\n\n")
    sink.write(_to_preview(family))
    sink.write("\n")


def _to_json(family: ExtractedFamily) -> str:
    return json.dumps(_as_plain_dict(family), indent=2, sort_keys=False)


def _as_plain_dict(family: ExtractedFamily) -> dict[str, Any]:
    return {
        "proband": _normalise(asdict(family.proband)),
        **{
            key: _normalise(asdict(getattr(family, key)))
            for key, _ in _RELATIVE_LABELS
            if getattr(family, key) is not None
        },
        "siblings": [_normalise(asdict(sibling)) for sibling in family.siblings],
    }


def _normalise(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalise(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _to_preview(family: ExtractedFamily) -> str:
    lines = ["Extracted family"]
    proband = family.proband
    sex = proband.biological_sex.value
    year = _format_year(proband.year_of_birth)
    lines.append(f"  proband  {proband.display_name} ({sex}{year})")
    for attr, label in _RELATIVE_LABELS:
        entry: RelativeEntry | None = getattr(family, attr)
        if entry is not None:
            lines.append(f"  {label:<22} {_format_relative(entry)}")
    if family.siblings:
        lines.append("  siblings")
        for sibling in family.siblings:
            lines.append(f"    - {_format_sibling(sibling)}")
    return "\n".join(lines)


def _format_relative(entry: RelativeEntry) -> str:
    return _with_notes(f"{entry.display_name}{_format_year(entry.year_of_birth)}", entry.notes)


def _format_sibling(sibling: SiblingEntry) -> str:
    year = _format_year(sibling.year_of_birth)
    header = f"{sibling.display_name} ({sibling.relation.value}{year})"
    return _with_notes(header, sibling.notes)


def _format_year(year: int | None) -> str:
    return f", b.{year}" if year is not None else ""


def _with_notes(header: str, notes: str | None) -> str:
    return f"{header} -- {notes}" if notes else header
