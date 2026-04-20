import json
from pathlib import Path
from typing import Any, cast

import pytest

from voice_driven_intake.extracted_family import BiologicalSex
from voice_driven_intake.extraction_schema import ExtractionSchemaError
from voice_driven_intake.text_extractor import LlmRequest, TextExtractor

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "sample-extraction.json"


def _sample() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(FIXTURE.read_text(encoding="utf-8")))


class _FakeGateway:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.last_request: LlmRequest | None = None

    def invoke_tool(self, request: LlmRequest) -> dict[str, Any]:
        self.last_request = request
        return self._payload


def test_extractor_forwards_transcript_and_parses_payload() -> None:
    gateway = _FakeGateway(_sample())

    family = TextExtractor(gateway, model="test-model").extract("a transcript")

    assert gateway.last_request is not None
    assert gateway.last_request.model == "test-model"
    assert gateway.last_request.user_prompt == "a transcript"
    assert gateway.last_request.temperature == 0.0
    assert family.proband.biological_sex is BiologicalSex.FEMALE
    assert family.proband.display_name == "Emma Carter"
    assert len(family.siblings) == 2


def test_schema_mismatch_raises_schema_error() -> None:
    gateway = _FakeGateway({"proband": {"display_name": "Emma"}, "siblings": []})

    with pytest.raises(ExtractionSchemaError):
        TextExtractor(gateway).extract("a transcript")
