import io
import json

from pedigree_ocr.extracted_family import (
    AffectionStatus,
    BiologicalSex,
    ExtractedFamily,
    ProbandEntry,
    RelativeEntry,
    SiblingEntry,
    SiblingRelation,
)
from pedigree_ocr.presenter import present


def _family() -> ExtractedFamily:
    return ExtractedFamily(
        proband=ProbandEntry(
            display_name="Emma",
            biological_sex=BiologicalSex.FEMALE,
            affection_status=AffectionStatus.CLEAR,
        ),
        mother=RelativeEntry(display_name="Grace"),
        maternal_grandmother=RelativeEntry(
            display_name="Edith",
            affection_status=AffectionStatus.AFFECTED,
            notes="Filled circle, slash; deceased.",
        ),
        siblings=(
            SiblingEntry(
                display_name="Alice",
                relation=SiblingRelation.SISTER,
                affection_status=AffectionStatus.AFFECTED,
            ),
        ),
    )


def test_present_emits_valid_json_followed_by_preview() -> None:
    buffer = io.StringIO()

    present(_family(), buffer)

    text = buffer.getvalue()
    json_part, preview_part = text.split("\n\n", 1)
    parsed = json.loads(json_part)
    assert parsed["proband"]["display_name"] == "Emma"
    assert parsed["proband"]["affection_status"] == "clear"
    assert parsed["maternal_grandmother"]["affection_status"] == "affected"
    assert parsed["siblings"][0]["relation"] == "sister"
    assert "Extracted family" in preview_part
    assert "[affected]" in preview_part
    assert "Edith" in preview_part


def test_present_omits_absent_relatives_from_json() -> None:
    buffer = io.StringIO()

    present(_family(), buffer)

    parsed = json.loads(buffer.getvalue().split("\n\n", 1)[0])
    assert "father" not in parsed
    assert "paternal_grandmother" not in parsed


def test_clear_status_is_not_shown_in_preview() -> None:
    buffer = io.StringIO()

    present(_family(), buffer)

    preview = buffer.getvalue().split("\n\n", 1)[1]
    proband_line = next(line for line in preview.splitlines() if line.startswith("  proband"))
    assert "[clear]" not in proband_line
