"""Parse ``POST /risk/calculate`` NICE responses into a domain value object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NiceCategory(str, Enum):
    NEAR_POPULATION = "near_population"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class NiceResult:
    category: NiceCategory
    triggers: tuple[str, ...]


class ResponseSchemaError(ValueError):
    """Raised when the Evagene response does not match the documented NICE schema."""


def parse_nice_response(payload: dict[str, Any]) -> NiceResult:
    cancer_risk = _require_dict(payload, "cancer_risk")
    return NiceResult(
        category=_parse_category(_require_str(cancer_risk, "nice_category")),
        triggers=_require_str_list(cancer_risk, "nice_triggers"),
    )


def _parse_category(raw: str) -> NiceCategory:
    try:
        return NiceCategory(raw)
    except ValueError as exc:
        raise ResponseSchemaError(f"Unknown NICE category: {raw!r}") from exc


def _require_dict(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise ResponseSchemaError(f"Response field {key!r} is missing or not an object.")
    return value


def _require_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str):
        raise ResponseSchemaError(f"Response field {key!r} is missing or not a string.")
    return value


def _require_str_list(container: dict[str, Any], key: str) -> tuple[str, ...]:
    value = container.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ResponseSchemaError(f"Response field {key!r} is not a list of strings.")
    return tuple(value)
