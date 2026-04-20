"""Pure handlers that map (tool name + arguments) -> JSON-ready result.

Each tool is exposed as a :class:`ToolSpec` — name, human-readable
description, JSON Schema for the inputs, and an async handler that
receives a validated :class:`EvageneClient` and the raw arguments.

The specs are the single source of truth for both the MCP ``list_tools``
response and dispatch in :func:`handle_call`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

JsonObject = dict[str, Any]
JsonSchema = dict[str, Any]


class EvageneClientProtocol(Protocol):
    """Subset of :class:`EvageneClient` that tool handlers depend on."""

    async def list_pedigrees(self) -> list[dict[str, Any]]: ...
    async def get_pedigree(self, pedigree_id: str) -> dict[str, Any]: ...
    async def describe_pedigree(self, pedigree_id: str) -> str: ...
    async def list_risk_models(self, pedigree_id: str) -> dict[str, Any]: ...
    async def calculate_risk(
        self,
        pedigree_id: str,
        *,
        model: str,
        counselee_id: str | None = None,
    ) -> dict[str, Any]: ...
    async def create_individual(
        self,
        *,
        display_name: str,
        biological_sex: str,
    ) -> dict[str, Any]: ...
    async def add_individual_to_pedigree(
        self,
        pedigree_id: str,
        individual_id: str,
    ) -> dict[str, Any]: ...
    async def add_relative(
        self,
        pedigree_id: str,
        *,
        relative_of: str,
        relative_type: str,
        display_name: str = "",
        biological_sex: str | None = None,
    ) -> dict[str, Any]: ...


Handler = Callable[[EvageneClientProtocol, Mapping[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: JsonSchema
    handler: Handler


class ToolArgumentError(ValueError):
    """Raised when a tool is called with missing or malformed arguments."""


# ----------------------------------------------------------------------
# Handlers — one per tool
# ----------------------------------------------------------------------


async def _list_pedigrees(
    client: EvageneClientProtocol, _args: Mapping[str, Any],
) -> list[JsonObject]:
    pedigrees = await client.list_pedigrees()
    return [_summarise_pedigree(item) for item in pedigrees]


async def _get_pedigree(client: EvageneClientProtocol, args: Mapping[str, Any]) -> JsonObject:
    pedigree_id = _require_str(args, "pedigree_id")
    return await client.get_pedigree(pedigree_id)


async def _describe_pedigree(client: EvageneClientProtocol, args: Mapping[str, Any]) -> JsonObject:
    pedigree_id = _require_str(args, "pedigree_id")
    text = await client.describe_pedigree(pedigree_id)
    return {"pedigree_id": pedigree_id, "description": text}


async def _list_risk_models(client: EvageneClientProtocol, args: Mapping[str, Any]) -> JsonObject:
    pedigree_id = _require_str(args, "pedigree_id")
    return await client.list_risk_models(pedigree_id)


async def _calculate_risk(client: EvageneClientProtocol, args: Mapping[str, Any]) -> JsonObject:
    pedigree_id = _require_str(args, "pedigree_id")
    model = _require_str(args, "model")
    counselee_id = _optional_str(args, "counselee_id")
    return await client.calculate_risk(
        pedigree_id, model=model, counselee_id=counselee_id,
    )


async def _add_individual(client: EvageneClientProtocol, args: Mapping[str, Any]) -> JsonObject:
    pedigree_id = _require_str(args, "pedigree_id")
    display_name = _require_str(args, "display_name")
    biological_sex = _require_str(args, "biological_sex")

    individual = await client.create_individual(
        display_name=display_name, biological_sex=biological_sex,
    )
    individual_id = _require_str(individual, "id")
    await client.add_individual_to_pedigree(pedigree_id, individual_id)
    return {"pedigree_id": pedigree_id, "individual": individual}


async def _add_relative(client: EvageneClientProtocol, args: Mapping[str, Any]) -> JsonObject:
    pedigree_id = _require_str(args, "pedigree_id")
    return await client.add_relative(
        pedigree_id,
        relative_of=_require_str(args, "relative_of"),
        relative_type=_require_str(args, "relative_type"),
        display_name=_optional_str(args, "display_name") or "",
        biological_sex=_optional_str(args, "biological_sex"),
    )


# ----------------------------------------------------------------------
# Tool catalogue
# ----------------------------------------------------------------------


_PEDIGREE_ID_SCHEMA: JsonSchema = {
    "type": "string",
    "description": "UUID of the pedigree.",
}

_BIOLOGICAL_SEX_SCHEMA: JsonSchema = {
    "type": "string",
    "enum": ["male", "female", "unknown"],
    "description": "Biological sex of the individual.",
}


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="list_pedigrees",
        description="List all pedigrees owned by the authenticated user.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        handler=_list_pedigrees,
    ),
    ToolSpec(
        name="get_pedigree",
        description="Fetch the full pedigree detail — individuals, relationships, eggs, diseases.",
        input_schema={
            "type": "object",
            "properties": {"pedigree_id": _PEDIGREE_ID_SCHEMA},
            "required": ["pedigree_id"],
            "additionalProperties": False,
        },
        handler=_get_pedigree,
    ),
    ToolSpec(
        name="describe_pedigree",
        description=(
            "Generate a structured English description of the pedigree, "
            "suitable for clinical reasoning."
        ),
        input_schema={
            "type": "object",
            "properties": {"pedigree_id": _PEDIGREE_ID_SCHEMA},
            "required": ["pedigree_id"],
            "additionalProperties": False,
        },
        handler=_describe_pedigree,
    ),
    ToolSpec(
        name="list_risk_models",
        description=(
            "List the risk models available for this pedigree "
            "(e.g. NICE, TYRER_CUZICK, BRCAPRO)."
        ),
        input_schema={
            "type": "object",
            "properties": {"pedigree_id": _PEDIGREE_ID_SCHEMA},
            "required": ["pedigree_id"],
            "additionalProperties": False,
        },
        handler=_list_risk_models,
    ),
    ToolSpec(
        name="calculate_risk",
        description="Run a named risk model against the pedigree and return the structured result.",
        input_schema={
            "type": "object",
            "properties": {
                "pedigree_id": _PEDIGREE_ID_SCHEMA,
                "model": {
                    "type": "string",
                    "description": (
                        "Risk-model enum, e.g. NICE, TYRER_CUZICK, "
                        "CLAUS, BRCAPRO, AUTOSOMAL_DOMINANT."
                    ),
                },
                "counselee_id": {
                    "type": "string",
                    "description": (
                        "Optional UUID of the target individual; "
                        "defaults to the proband."
                    ),
                },
            },
            "required": ["pedigree_id", "model"],
            "additionalProperties": False,
        },
        handler=_calculate_risk,
    ),
    ToolSpec(
        name="add_individual",
        description=(
            "Create a new individual and attach them to the pedigree. "
            "Returns the stored individual."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "pedigree_id": _PEDIGREE_ID_SCHEMA,
                "display_name": {"type": "string", "description": "Human-readable name."},
                "biological_sex": _BIOLOGICAL_SEX_SCHEMA,
            },
            "required": ["pedigree_id", "display_name", "biological_sex"],
            "additionalProperties": False,
        },
        handler=_add_individual,
    ),
    ToolSpec(
        name="add_relative",
        description=(
            "Add a new individual related to an existing one "
            "by kinship type (father, sister, cousin, etc.)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "pedigree_id": _PEDIGREE_ID_SCHEMA,
                "relative_of": {
                    "type": "string",
                    "description": "UUID of the existing individual whose relative is being added.",
                },
                "relative_type": {
                    "type": "string",
                    "description": (
                        "Kinship enum: father, mother, son, daughter, brother, sister, "
                        "half_brother, half_sister, paternal_grandfather, paternal_grandmother, "
                        "maternal_grandfather, maternal_grandmother, grandson, granddaughter, "
                        "paternal_uncle, paternal_aunt, maternal_uncle, maternal_aunt, "
                        "nephew, niece, first_cousin, partner, step_father, step_mother, unrelated."
                    ),
                },
                "display_name": {
                    "type": "string",
                    "description": "Optional human-readable name for the new individual.",
                },
                "biological_sex": _BIOLOGICAL_SEX_SCHEMA,
            },
            "required": ["pedigree_id", "relative_of", "relative_type"],
            "additionalProperties": False,
        },
        handler=_add_relative,
    ),
)


_TOOLS_BY_NAME: dict[str, ToolSpec] = {spec.name: spec for spec in TOOL_SPECS}


async def handle_call(
    client: EvageneClientProtocol,
    name: str,
    arguments: Mapping[str, Any],
) -> Any:
    spec = _TOOLS_BY_NAME.get(name)
    if spec is None:
        raise ToolArgumentError(f"Unknown tool: {name}")
    return await spec.handler(client, arguments)


# ----------------------------------------------------------------------
# Argument helpers
# ----------------------------------------------------------------------


def _require_str(source: Mapping[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ToolArgumentError(f"Missing or empty string field: {key!r}")
    return value


def _optional_str(source: Mapping[str, Any], key: str) -> str | None:
    value = source.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ToolArgumentError(f"Field {key!r} must be a string when provided")
    return value or None


def _summarise_pedigree(item: Any) -> JsonObject:
    if not isinstance(item, dict):
        raise ToolArgumentError(f"Expected pedigree object, got {type(item).__name__}")
    return {
        "id": item.get("id"),
        "display_name": item.get("display_name"),
        "date_represented": item.get("date_represented"),
        "disease_ids": item.get("disease_ids", []),
    }
