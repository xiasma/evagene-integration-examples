import pytest

from evagene_mcp.tool_handlers import TOOL_SPECS, ToolArgumentError, handle_call

from .fakes import FakeClient

_PEDIGREE_ID = "3d7b9b2e-4f3a-4b2d-9a1c-2e0a2b3c4d5e"
_PROBAND_ID = "11111111-1111-1111-1111-111111111111"


def test_every_tool_has_a_json_schema() -> None:
    for spec in TOOL_SPECS:
        assert spec.input_schema["type"] == "object"
        assert "properties" in spec.input_schema


async def test_list_pedigrees_summarises_items() -> None:
    client = FakeClient(
        list_pedigrees_result=[
            {
                "id": _PEDIGREE_ID,
                "display_name": "BRCA family",
                "date_represented": "2024-06-01",
                "disease_ids": ["d1"],
                "owner": "user-1",
            }
        ]
    )

    result = await handle_call(client, "list_pedigrees", {})

    assert result == [
        {
            "id": _PEDIGREE_ID,
            "display_name": "BRCA family",
            "date_represented": "2024-06-01",
            "disease_ids": ["d1"],
        }
    ]


async def test_get_pedigree_forwards_id() -> None:
    client = FakeClient(get_pedigree_result={"id": _PEDIGREE_ID})

    result = await handle_call(client, "get_pedigree", {"pedigree_id": _PEDIGREE_ID})
    assert result == {"id": _PEDIGREE_ID}
    assert client.calls[0] == ("get_pedigree", {"pedigree_id": _PEDIGREE_ID})


async def test_describe_pedigree_wraps_text() -> None:
    client = FakeClient(describe_pedigree_result="A two-generation family...")

    result = await handle_call(client, "describe_pedigree", {"pedigree_id": _PEDIGREE_ID})
    assert result == {"pedigree_id": _PEDIGREE_ID, "description": "A two-generation family..."}


async def test_calculate_risk_passes_model_and_counselee() -> None:
    client = FakeClient(calculate_risk_result={"model": "NICE"})

    await handle_call(        client,
        "calculate_risk",
        {"pedigree_id": _PEDIGREE_ID, "model": "NICE", "counselee_id": _PROBAND_ID},
    )

    assert client.calls[0] == (
        "calculate_risk",
        {"pedigree_id": _PEDIGREE_ID, "model": "NICE", "counselee_id": _PROBAND_ID},
    )


async def test_calculate_risk_requires_model() -> None:
    client = FakeClient()

    with pytest.raises(ToolArgumentError):
        await handle_call(client, "calculate_risk", {"pedigree_id": _PEDIGREE_ID})

async def test_add_individual_creates_and_attaches() -> None:
    client = FakeClient(
        create_individual_result={"id": _PROBAND_ID, "display_name": "Proband"},
    )

    result = await handle_call(        client,
        "add_individual",
        {
            "pedigree_id": _PEDIGREE_ID,
            "display_name": "Proband",
            "biological_sex": "female",
        },
    )

    assert result["pedigree_id"] == _PEDIGREE_ID
    assert result["individual"]["id"] == _PROBAND_ID
    assert [call[0] for call in client.calls] == [
        "create_individual",
        "add_individual_to_pedigree",
    ]


async def test_add_relative_passes_kinship_fields() -> None:
    client = FakeClient(add_relative_result={"individual": {"id": "x"}})

    await handle_call(        client,
        "add_relative",
        {
            "pedigree_id": _PEDIGREE_ID,
            "relative_of": _PROBAND_ID,
            "relative_type": "sister",
            "display_name": "Jane",
            "biological_sex": "female",
        },
    )

    assert client.calls[0] == (
        "add_relative",
        {
            "pedigree_id": _PEDIGREE_ID,
            "relative_of": _PROBAND_ID,
            "relative_type": "sister",
            "display_name": "Jane",
            "biological_sex": "female",
        },
    )


async def test_unknown_tool_raises() -> None:
    client = FakeClient()

    with pytest.raises(ToolArgumentError):
        await handle_call(client, "does_not_exist", {})
