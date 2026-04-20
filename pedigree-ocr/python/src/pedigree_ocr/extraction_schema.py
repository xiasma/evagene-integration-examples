"""JSON schema the vision tool is asked to fill, and the pure parser
that turns a conforming dict into :class:`ExtractedFamily`.

Kept separate from the Anthropic-specific code so tests can exercise
schema + parser without any LLM involvement, and so a reader can audit
exactly what the model is asked to produce from the drawing.
"""

from __future__ import annotations

from typing import Any

from .extracted_family import (
    AffectionStatus,
    BiologicalSex,
    ExtractedFamily,
    ProbandEntry,
    RelativeEntry,
    SiblingEntry,
    SiblingRelation,
)

TOOL_NAME = "record_extracted_family"
TOOL_DESCRIPTION = (
    "Record the proband plus any first- and second-degree relatives you can identify "
    "in the hand-drawn pedigree image. Only include a relative if you can see them "
    "in the drawing. Map pedigree conventions to the schema: square = male, circle = "
    "female, filled-in = affected, half-filled = carrier, slash through symbol = "
    "deceased, double horizontal line between a couple = consanguineous. If a symbol "
    "is ambiguous (e.g. an unclear twin chevron, a partial slash), put the doubt in "
    "that relative's 'notes' field in plain prose rather than guessing a status."
)

SYSTEM_PROMPT = (
    "You are a pedigree-image extraction assistant for genetic counselling. "
    "You will be shown a photograph or scan of a hand-drawn pedigree -- the kind a "
    "counsellor sketches during a consult, or a textbook figure. "
    "Call the record_extracted_family tool exactly once with the family structure "
    "you can see. "
    "Identify the proband (usually marked with an arrow) and, where drawn, the "
    "mother, father, four grandparents, and full or half siblings. "
    "Read pedigree symbols strictly: square=male, circle=female, diamond=unknown sex; "
    "a filled-in shape means clinically affected; a half-filled or dotted shape means "
    "carrier; a diagonal slash through the shape means deceased; a double horizontal "
    "line between a couple means consanguinity; MZ twins share a chevron joining their "
    "lines below the parents. "
    "If any of these symbols is unclear or does not fit the schema (twins, "
    "consanguinity, multiple marriages, step-relatives), describe what you see in "
    "plain prose in the relevant 'notes' field -- do not invent a mapping. "
    "If a relative is not in the drawing, omit them rather than guessing. "
    "If year of birth, age, or age-at-diagnosis is written next to a symbol, put it "
    "in 'notes' verbatim; only set 'year_of_birth' when an unambiguous four-digit "
    "year is written on the drawing."
)


class ExtractionSchemaError(ValueError):
    """Raised when the model's tool-use input does not match the schema."""


def build_tool_schema() -> dict[str, Any]:
    """The JSON Schema given to Anthropic's tool-use interface."""
    return {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["proband", "siblings"],
            "properties": {
                "proband": _proband_schema(),
                "mother": _relative_schema(),
                "father": _relative_schema(),
                "maternal_grandmother": _relative_schema(),
                "maternal_grandfather": _relative_schema(),
                "paternal_grandmother": _relative_schema(),
                "paternal_grandfather": _relative_schema(),
                "siblings": {
                    "type": "array",
                    "items": _sibling_schema(),
                },
            },
        },
    }


def parse_extraction(payload: dict[str, Any]) -> ExtractedFamily:
    """Convert a tool-use ``input`` dict into an :class:`ExtractedFamily`."""
    return ExtractedFamily(
        proband=_parse_proband(_require_object(payload, "proband")),
        mother=_parse_optional_relative(payload.get("mother")),
        father=_parse_optional_relative(payload.get("father")),
        maternal_grandmother=_parse_optional_relative(payload.get("maternal_grandmother")),
        maternal_grandfather=_parse_optional_relative(payload.get("maternal_grandfather")),
        paternal_grandmother=_parse_optional_relative(payload.get("paternal_grandmother")),
        paternal_grandfather=_parse_optional_relative(payload.get("paternal_grandfather")),
        siblings=_parse_siblings(payload.get("siblings")),
    )


def _proband_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["display_name", "biological_sex", "affection_status"],
        "properties": {
            "display_name": {"type": "string"},
            "biological_sex": {"type": "string", "enum": [e.value for e in BiologicalSex]},
            "affection_status": _affection_schema(),
            "year_of_birth": _nullable_year(),
            "notes": _nullable_string(),
        },
    }


def _relative_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["display_name", "affection_status"],
        "properties": {
            "display_name": {"type": "string"},
            "affection_status": _affection_schema(),
            "year_of_birth": _nullable_year(),
            "notes": _nullable_string(),
        },
    }


def _sibling_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["display_name", "relation", "affection_status"],
        "properties": {
            "display_name": {"type": "string"},
            "relation": {"type": "string", "enum": [e.value for e in SiblingRelation]},
            "affection_status": _affection_schema(),
            "year_of_birth": _nullable_year(),
            "notes": _nullable_string(),
        },
    }


def _affection_schema() -> dict[str, Any]:
    return {"type": "string", "enum": [e.value for e in AffectionStatus]}


def _nullable_year() -> dict[str, Any]:
    return {"type": ["integer", "null"], "minimum": 1850, "maximum": 2030}


def _nullable_string() -> dict[str, Any]:
    return {"type": ["string", "null"]}


def _parse_proband(payload: dict[str, Any]) -> ProbandEntry:
    return ProbandEntry(
        display_name=_require_non_empty_string(payload, "display_name"),
        biological_sex=_parse_sex(_require_string(payload, "biological_sex")),
        affection_status=_parse_affection(_require_string(payload, "affection_status")),
        year_of_birth=_optional_year(payload, "year_of_birth"),
        notes=_optional_string(payload, "notes"),
    )


def _parse_optional_relative(payload: Any) -> RelativeEntry | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ExtractionSchemaError("Relative entry must be an object or null.")
    return RelativeEntry(
        display_name=_require_non_empty_string(payload, "display_name"),
        affection_status=_parse_affection(_require_string(payload, "affection_status")),
        year_of_birth=_optional_year(payload, "year_of_birth"),
        notes=_optional_string(payload, "notes"),
    )


def _parse_siblings(payload: Any) -> tuple[SiblingEntry, ...]:
    if payload is None:
        return ()
    if not isinstance(payload, list):
        raise ExtractionSchemaError("Field 'siblings' must be an array.")
    return tuple(_parse_sibling(item) for item in payload)


def _parse_sibling(payload: Any) -> SiblingEntry:
    if not isinstance(payload, dict):
        raise ExtractionSchemaError("Each sibling entry must be an object.")
    return SiblingEntry(
        display_name=_require_non_empty_string(payload, "display_name"),
        relation=_parse_sibling_relation(_require_string(payload, "relation")),
        affection_status=_parse_affection(_require_string(payload, "affection_status")),
        year_of_birth=_optional_year(payload, "year_of_birth"),
        notes=_optional_string(payload, "notes"),
    )


def _parse_sex(raw: str) -> BiologicalSex:
    try:
        return BiologicalSex(raw)
    except ValueError as exc:
        raise ExtractionSchemaError(f"Unknown biological_sex: {raw!r}") from exc


def _parse_affection(raw: str) -> AffectionStatus:
    try:
        return AffectionStatus(raw)
    except ValueError as exc:
        raise ExtractionSchemaError(f"Unknown affection_status: {raw!r}") from exc


def _parse_sibling_relation(raw: str) -> SiblingRelation:
    try:
        return SiblingRelation(raw)
    except ValueError as exc:
        raise ExtractionSchemaError(f"Unknown sibling relation: {raw!r}") from exc


def _require_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ExtractionSchemaError(f"Missing required object field {key!r}.")
    return value


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ExtractionSchemaError(f"Missing required string field {key!r}.")
    return value


def _require_non_empty_string(payload: dict[str, Any], key: str) -> str:
    value = _require_string(payload, key)
    stripped = value.strip()
    if not stripped:
        raise ExtractionSchemaError(f"Field {key!r} must be a non-empty string.")
    return stripped


def _optional_year(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExtractionSchemaError(f"Field {key!r} must be an integer or null.")
    return int(value)


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ExtractionSchemaError(f"Field {key!r} must be a string or null.")
    stripped = value.strip()
    return stripped or None
