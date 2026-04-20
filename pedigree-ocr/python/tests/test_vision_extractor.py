import json
from pathlib import Path
from typing import Any, cast

import pytest

from pedigree_ocr.extracted_family import AffectionStatus, BiologicalSex
from pedigree_ocr.extraction_schema import ExtractionSchemaError
from pedigree_ocr.image_source import PNG_MEDIA_TYPE, LoadedImage
from pedigree_ocr.vision_extractor import (
    VisionExtractor,
    VisionRequest,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "sample-extraction.json"


def _sample() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(FIXTURE.read_text(encoding="utf-8")))


def _image() -> LoadedImage:
    return LoadedImage(data=b"PNG-bytes-here", media_type=PNG_MEDIA_TYPE)


class _FakeGateway:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.last_request: VisionRequest | None = None

    def invoke_tool(self, request: VisionRequest) -> dict[str, Any]:
        self.last_request = request
        return self._payload


def test_extractor_passes_image_and_tool_schema_to_gateway_and_parses_payload() -> None:
    gateway = _FakeGateway(_sample())

    family = VisionExtractor(gateway, model="test-model").extract(_image())

    request = gateway.last_request
    assert request is not None
    assert request.model == "test-model"
    assert request.temperature is None
    assert request.image.media_type == PNG_MEDIA_TYPE
    assert request.image.data == b"PNG-bytes-here"
    assert request.tool["name"] == "record_extracted_family"
    assert family.proband.display_name == "Emma"
    assert family.proband.biological_sex is BiologicalSex.FEMALE
    assert family.maternal_grandmother is not None
    assert family.maternal_grandmother.affection_status is AffectionStatus.AFFECTED


def test_schema_mismatch_raises_schema_error() -> None:
    gateway = _FakeGateway({"proband": {"display_name": "Emma"}, "siblings": []})

    with pytest.raises(ExtractionSchemaError):
        VisionExtractor(gateway).extract(_image())
