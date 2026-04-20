"""Pure transform: (PedigreeDetail, LabelStyle) -> {individual_id: new_label}.

The mapping's keys are individual IDs, so any caller can join it back to
other pedigree-level data.  The SVG deidentifier joins on the original
display name (see ``app.py``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .config import LabelStyle

_UNKNOWN_GENERATION_MARK = "?"


def build_label_mapping(
    detail: Mapping[str, Any],
    label_style: LabelStyle,
) -> dict[str, str]:
    """Return an ``individual_id -> new_label`` mapping in the requested style."""
    individuals = detail.get("individuals") or []
    if not isinstance(individuals, list):
        raise ValueError("detail['individuals'] is not a list")

    if label_style is LabelStyle.OFF:
        return {_require_id(ind): "" for ind in individuals}
    if label_style is LabelStyle.INITIALS:
        return {_require_id(ind): _initials_of(_display_name(ind)) for ind in individuals}
    if label_style is LabelStyle.GENERATION_NUMBER:
        return _generation_number_labels(individuals)
    raise ValueError(f"Unknown label style: {label_style!r}")


def _generation_number_labels(individuals: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    # Prefer the explicit `generation` field; fall back on the vertical
    # layout coordinate (smaller y = higher up the page = earlier
    # generation), which is the standard clinical-genetics rendering
    # convention.  Individuals with neither fall back to "?-n".
    resolved = [(_require_id(ind), _generation_key(ind)) for ind in individuals]
    ordered_keys = sorted({key for _, key in resolved if key is not None})
    roman_of = {key: _to_roman(index + 1) for index, key in enumerate(ordered_keys)}

    counts: dict[_GenerationKey, int] = dict.fromkeys(ordered_keys, 0)
    labels: dict[str, str] = {}
    unknown_index = 0
    for ind_id, key in resolved:
        if key is None:
            unknown_index += 1
            labels[ind_id] = f"{_UNKNOWN_GENERATION_MARK}-{unknown_index}"
            continue
        counts[key] += 1
        labels[ind_id] = f"{roman_of[key]}-{counts[key]}"
    return labels


_GenerationKey = tuple[int, float]


def _generation_key(individual: Mapping[str, Any]) -> _GenerationKey | None:
    # A two-part key keeps explicit generation numbers and inferred
    # y-coordinate buckets distinct when a pedigree mixes the two, while
    # still letting the comparator produce a total ordering.  The first
    # element is a source-priority tag so explicit > inferred when both
    # are present in the same pedigree.
    generation = individual.get("generation")
    if not isinstance(generation, bool) and isinstance(generation, int):
        return (0, float(generation))
    y = individual.get("y")
    if not isinstance(y, bool) and isinstance(y, int | float):
        return (1, float(y))
    return None


def _initials_of(name: str) -> str:
    tokens = [token for token in name.split() if token]
    return "".join(token[0].upper() for token in tokens)


def _display_name(individual: Mapping[str, Any]) -> str:
    value = individual.get("display_name", "")
    return value if isinstance(value, str) else ""


def _require_id(individual: Mapping[str, Any]) -> str:
    value = individual.get("id")
    if not isinstance(value, str) or not value:
        raise ValueError("individual is missing a string 'id' field")
    return value


# ---------------------------------------------------------------------------
# Roman numerals.  Handles 1..3999, which covers any real pedigree generation
# depth by six orders of magnitude; simpler than pulling in a dependency.
# ---------------------------------------------------------------------------

_ROMAN_PAIRS: tuple[tuple[int, str], ...] = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)
_MIN_ROMAN = 1
_MAX_ROMAN = 3999


def _to_roman(value: int) -> str:
    if value < _MIN_ROMAN or value > _MAX_ROMAN:
        raise ValueError(f"cannot render {value} as a Roman numeral")
    out: list[str] = []
    remaining = value
    for number, glyph in _ROMAN_PAIRS:
        while remaining >= number:
            out.append(glyph)
            remaining -= number
    return "".join(out)
