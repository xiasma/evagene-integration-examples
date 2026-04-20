"""Parse the Evagene ``risk/calculate`` response into a domain ``NiceOutcome``."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskCategory(str, Enum):
    NEAR_POPULATION = "near_population"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class NiceOutcome:
    counselee_name: str
    category: RiskCategory
    refer_for_genetics_assessment: bool
    triggers: tuple[str, ...]
    notes: tuple[str, ...]


class ResponseSchemaError(ValueError):
    """Raised when the Evagene response does not match the documented NICE schema."""


def classify_nice_response(payload: dict[str, Any]) -> NiceOutcome:
    """Extract a :class:`NiceOutcome` from a ``/risk/calculate`` response.

    Strict by design — a silent default here would mask a server-side
    breaking change and leave the caller reasoning over stale assumptions.
    """
    cancer_risk = _require_dict(payload, "cancer_risk")
    return NiceOutcome(
        counselee_name=_optional_str(payload, "counselee_name"),
        category=_parse_category(_require_str(cancer_risk, "nice_category")),
        refer_for_genetics_assessment=_require_bool(cancer_risk, "nice_refer_genetics"),
        triggers=_require_str_list(cancer_risk, "nice_triggers"),
        notes=_require_str_list(cancer_risk, "notes"),
    )


def _parse_category(raw: str) -> RiskCategory:
    try:
        return RiskCategory(raw)
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


def _require_bool(container: dict[str, Any], key: str) -> bool:
    value = container.get(key)
    if not isinstance(value, bool):
        raise ResponseSchemaError(f"Response field {key!r} is missing or not a bool.")
    return value


def _require_str_list(container: dict[str, Any], key: str) -> tuple[str, ...]:
    value = container.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ResponseSchemaError(f"Response field {key!r} is not a list of strings.")
    return tuple(value)


def _optional_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    return value if isinstance(value, str) else ""
