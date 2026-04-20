"""JSON schema the LLM tool is asked to fill, and the pure parser that
turns a conforming dict into :class:`ExtractedFamily`.

The system prompt is tuned for *spoken* transcripts: Whisper output
contains self-corrections, filler words, and occasional mishearings
that a reader of written call notes would not see.
"""

from __future__ import annotations

from typing import Any

from .extracted_family import (
    BiologicalSex,
    ExtractedFamily,
    ProbandEntry,
    RelativeEntry,
    SiblingEntry,
    SiblingRelation,
)

TOOL_NAME = "record_extracted_family"
TOOL_DESCRIPTION = (
    "Record the first- and second-degree relatives you were able to identify in the "
    "transcript. Only include a relative if the transcript mentions them. Keep names "
    "as given. Put any disease, diagnosis, age-at-diagnosis or death details in the "
    "relative's 'notes' field in plain prose -- do not invent structure for them."
)

SYSTEM_PROMPT = (
    "You are a family-history extraction assistant for genetic counselling. "
    "The input is a Whisper transcript of a clinician dictating or recording a "
    "spoken family history. Expect speech disfluencies -- filler words "
    "('um', 'er'), false starts, self-corrections, and occasional mishearings of "
    "proper names. Prefer the speaker's most recent restatement when they correct "
    "themselves (for example 'my aunt -- sorry, my sister'). "
    "If a name sounds phonetically wrong for a name you would expect, keep it as "
    "given rather than guessing. "
    "Read the transcript and call the record_extracted_family tool exactly once "
    "with the family structure you can identify. "
    "Include the proband and, when mentioned, the mother, father, four grandparents, "
    "and full or half siblings. "
    "If a relative is not mentioned, omit them rather than guessing. "
    "Put disease history, ages at diagnosis, and any free-text context into the "
    "per-relative 'notes' field. "
    "If a year of birth is stated or can be inferred directly (for example from "
    "'she is 42' in a session dated this year), fill year_of_birth; otherwise leave "
    "it null."
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
        "required": ["display_name", "biological_sex"],
        "properties": {
            "display_name": {"type": "string"},
            "biological_sex": {"type": "string", "enum": [e.value for e in BiologicalSex]},
            "year_of_birth": _nullable_year(),
            "notes": _nullable_string(),
        },
    }


def _relative_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["display_name"],
        "properties": {
            "display_name": {"type": "string"},
            "year_of_birth": _nullable_year(),
            "notes": _nullable_string(),
        },
    }


def _sibling_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["display_name", "relation"],
        "properties": {
            "display_name": {"type": "string"},
            "relation": {"type": "string", "enum": [e.value for e in SiblingRelation]},
            "year_of_birth": _nullable_year(),
            "notes": _nullable_string(),
        },
    }


def _nullable_year() -> dict[str, Any]:
    return {"type": ["integer", "null"], "minimum": 1850, "maximum": 2030}


def _nullable_string() -> dict[str, Any]:
    return {"type": ["string", "null"]}


def _parse_proband(payload: dict[str, Any]) -> ProbandEntry:
    return ProbandEntry(
        display_name=_require_non_empty_string(payload, "display_name"),
        biological_sex=_parse_sex(_require_string(payload, "biological_sex")),
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
        year_of_birth=_optional_year(payload, "year_of_birth"),
        notes=_optional_string(payload, "notes"),
    )


def _parse_sex(raw: str) -> BiologicalSex:
    try:
        return BiologicalSex(raw)
    except ValueError as exc:
        raise ExtractionSchemaError(f"Unknown biological_sex: {raw!r}") from exc


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
