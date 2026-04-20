"""Pure transform: per-model RiskResult payloads -> a ComparisonTable.

The schema is checked strictly: a silent default here would mask a
server-side change and leave the caller reasoning over stale numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FIXED_COLUMNS: tuple[str, ...] = ("Model", "Counselee", "Any carrier")
CARRIER_ANY_KEY = "Pr(Being a carrier)"
LIFETIME_COLUMN = "Lifetime risk @max-age"

# A row cell is a number (probability), a string (Model / Counselee /
# lifetime summary), or None for "this model doesn't populate this cell".
Cell = float | str | None


class ResponseSchemaError(ValueError):
    """Raised when a response payload does not match the BayesMendel schema."""


@dataclass(frozen=True)
class ComparisonTable:
    columns: tuple[str, ...]
    rows: tuple[dict[str, Cell], ...]


def build_comparison(payloads: dict[str, dict[str, Any]]) -> ComparisonTable:
    """Build a :class:`ComparisonTable` from a model-name-keyed payload dict.

    The key order of ``payloads`` becomes the row order of the table.
    """
    if not payloads:
        raise ResponseSchemaError("payloads must be a non-empty mapping")

    gene_columns = _gene_column_order(payloads)
    columns = (*FIXED_COLUMNS, *gene_columns, LIFETIME_COLUMN)

    rows = tuple(_build_row(name, payload, gene_columns) for name, payload in payloads.items())
    return ComparisonTable(columns=columns, rows=rows)


def _build_row(
    model_name: str,
    payload: dict[str, Any],
    gene_columns: tuple[str, ...],
) -> dict[str, Cell]:
    carrier_probs = _require_number_dict(payload, "carrier_probabilities")
    row: dict[str, Cell] = {
        "Model": model_name,
        "Counselee": _optional_str(payload, "counselee_name"),
        "Any carrier": carrier_probs.get(CARRIER_ANY_KEY),
    }
    for gene in gene_columns:
        row[gene] = carrier_probs.get(gene)
    row[LIFETIME_COLUMN] = _summarise_lifetime_risks(payload)
    return row


def _gene_column_order(payloads: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    seen: list[str] = []
    for payload in payloads.values():
        carrier_probs = payload.get("carrier_probabilities")
        if isinstance(carrier_probs, dict):
            for key in carrier_probs:
                if key != CARRIER_ANY_KEY and key not in seen:
                    seen.append(key)
    return tuple(seen)


def _summarise_lifetime_risks(payload: dict[str, Any]) -> str | None:
    """Pick the oldest future-risk row and render it as ``"Label X.YZ%; ..."``."""
    future_risks = payload.get("future_risks")
    if not isinstance(future_risks, list) or not future_risks:
        return None

    oldest = _oldest_future_risk(future_risks)
    risks = oldest.get("risks")
    if not isinstance(risks, dict) or not risks:
        return None

    for value in risks.values():
        if not isinstance(value, int | float):
            raise ResponseSchemaError(
                f"future_risks.risks contains non-numeric value: {value!r}"
            )

    return "; ".join(f"{label} {_format_percent(value)}" for label, value in risks.items())


def _oldest_future_risk(future_risks: list[Any]) -> dict[str, Any]:
    valid = [entry for entry in future_risks if _has_numeric_age(entry)]
    if not valid:
        raise ResponseSchemaError("future_risks contains no numeric ages")
    return max(valid, key=lambda entry: int(entry["age"]))


def _has_numeric_age(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("age"), int | float)
        and not isinstance(entry.get("age"), bool)
    )


def _format_percent(value: float) -> str:
    return f"{100 * value:.2f}%"


def _require_number_dict(payload: dict[str, Any], key: str) -> dict[str, float]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ResponseSchemaError(f"field {key!r} is missing or not an object")
    for inner_key, inner_value in value.items():
        if not isinstance(inner_value, int | float) or isinstance(inner_value, bool):
            raise ResponseSchemaError(f"field {key}[{inner_key!r}] is not a number")
    return value


def _optional_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    return value if isinstance(value, str) else ""
