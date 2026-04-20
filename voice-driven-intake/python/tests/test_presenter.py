import io
import json

from voice_driven_intake.extracted_family import (
    BiologicalSex,
    ExtractedFamily,
    ProbandEntry,
    RelativeEntry,
    SiblingEntry,
    SiblingRelation,
)
from voice_driven_intake.presenter import present


def _family() -> ExtractedFamily:
    return ExtractedFamily(
        proband=ProbandEntry(
            display_name="Emma Carter",
            biological_sex=BiologicalSex.FEMALE,
            year_of_birth=1985,
        ),
        mother=RelativeEntry(display_name="Grace", year_of_birth=1957),
        maternal_grandmother=RelativeEntry(
            display_name="Edith",
            notes="Ovarian cancer, late fifties.",
        ),
        siblings=(
            SiblingEntry(
                display_name="Alice",
                relation=SiblingRelation.SISTER,
                year_of_birth=1983,
                notes="Breast cancer at 41.",
            ),
        ),
    )


def test_present_emits_valid_json_followed_by_preview() -> None:
    buffer = io.StringIO()

    present(_family(), buffer)

    text = buffer.getvalue()
    json_part, preview_part = text.split("\n\n", 1)
    parsed = json.loads(json_part)
    assert parsed["proband"]["display_name"] == "Emma Carter"
    assert parsed["proband"]["biological_sex"] == "female"
    assert parsed["siblings"][0]["relation"] == "sister"
    assert "Extracted family" in preview_part
    assert "Emma Carter" in preview_part
    assert "Alice" in preview_part
    assert "Breast cancer at 41." in preview_part


def test_present_omits_absent_relatives_from_json() -> None:
    buffer = io.StringIO()

    present(_family(), buffer)

    json_part = buffer.getvalue().split("\n\n", 1)[0]
    parsed = json.loads(json_part)
    assert "father" not in parsed
    assert "paternal_grandmother" not in parsed
