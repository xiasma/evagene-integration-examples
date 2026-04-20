import json
from pathlib import Path
from typing import Any, cast

import pytest

from call_notes_to_pedigree.extracted_family import (
    BiologicalSex,
    SiblingRelation,
)
from call_notes_to_pedigree.extraction_schema import (
    ExtractionSchemaError,
    build_tool_schema,
    parse_extraction,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "sample-extraction.json"


def _load_sample() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_tool_schema_has_name_description_and_input_schema() -> None:
    tool = build_tool_schema()
    assert tool["name"] == "record_extracted_family"
    assert isinstance(tool["description"], str) and tool["description"]
    input_schema = tool["input_schema"]
    assert input_schema["type"] == "object"
    assert input_schema["required"] == ["proband", "siblings"]
    properties = input_schema["properties"]
    assert set(properties.keys()) == {
        "proband",
        "mother",
        "father",
        "maternal_grandmother",
        "maternal_grandfather",
        "paternal_grandmother",
        "paternal_grandfather",
        "siblings",
    }


def test_tool_schema_is_valid_json() -> None:
    json.dumps(build_tool_schema())


def test_parse_sample_extraction_returns_expected_structure() -> None:
    family = parse_extraction(_load_sample())

    assert family.proband.display_name == "Emma Carter"
    assert family.proband.biological_sex is BiologicalSex.FEMALE
    assert family.proband.year_of_birth == 1985
    assert family.mother is not None and family.mother.display_name == "Grace"
    assert family.maternal_grandmother is not None
    assert family.maternal_grandmother.notes is not None
    assert "Ovarian cancer" in family.maternal_grandmother.notes
    assert len(family.siblings) == 2
    alice, ben = family.siblings
    assert alice.relation is SiblingRelation.SISTER
    assert ben.relation is SiblingRelation.HALF_BROTHER


def test_rejects_payload_missing_proband() -> None:
    with pytest.raises(ExtractionSchemaError):
        parse_extraction({"siblings": []})


def test_rejects_unknown_sex() -> None:
    with pytest.raises(ExtractionSchemaError):
        parse_extraction(
            {
                "proband": {
                    "display_name": "Emma",
                    "biological_sex": "robot",
                },
                "siblings": [],
            }
        )


def test_empty_note_is_treated_as_absent() -> None:
    family = parse_extraction(
        {
            "proband": {
                "display_name": "Emma",
                "biological_sex": "female",
                "notes": "   ",
            },
            "siblings": [],
        }
    )
    assert family.proband.notes is None
