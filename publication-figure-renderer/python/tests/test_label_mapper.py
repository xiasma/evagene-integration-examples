import json
from pathlib import Path
from typing import Any

from publication_figure_renderer.config import LabelStyle
from publication_figure_renderer.label_mapper import build_label_mapping

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _sample_detail() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (_FIXTURES / "sample-detail.json").read_text(encoding="utf-8")
    )
    return payload


def test_generation_number_style_assigns_roman_generation_and_sibling_number() -> None:
    mapping = build_label_mapping(_sample_detail(), LabelStyle.GENERATION_NUMBER)

    assert mapping["11111111-1111-1111-1111-111111111111"] == "I-1"
    assert mapping["22222222-2222-2222-2222-222222222222"] == "I-2"
    assert mapping["33333333-3333-3333-3333-333333333333"] == "II-1"
    assert mapping["44444444-4444-4444-4444-444444444444"] == "II-2"
    assert mapping["55555555-5555-5555-5555-555555555555"] == "III-1"


def test_initials_style_takes_first_letter_of_each_word() -> None:
    mapping = build_label_mapping(_sample_detail(), LabelStyle.INITIALS)

    assert mapping["11111111-1111-1111-1111-111111111111"] == "RS"
    assert mapping["55555555-5555-5555-5555-555555555555"] == "SS"


def test_off_style_produces_empty_labels_for_every_individual() -> None:
    mapping = build_label_mapping(_sample_detail(), LabelStyle.OFF)

    assert set(mapping.values()) == {""}
    assert len(mapping) == 5


def test_y_coordinate_falls_back_for_generation_when_generation_is_missing() -> None:
    # Real-world pedigrees frequently have no `generation` field set.
    # Fall back on the layout's y-coordinate: smaller y = earlier
    # generation (= higher up the page).
    detail: dict[str, Any] = {
        "individuals": [
            {"id": "11111111-1111-1111-1111-111111111111", "y": 560.0},
            {"id": "22222222-2222-2222-2222-222222222222", "y": 200.0},
            {"id": "33333333-3333-3333-3333-333333333333", "y": 360.0},
            {"id": "44444444-4444-4444-4444-444444444444", "y": 200.0},
        ]
    }

    mapping = build_label_mapping(detail, LabelStyle.GENERATION_NUMBER)

    assert mapping["22222222-2222-2222-2222-222222222222"] == "I-1"
    assert mapping["44444444-4444-4444-4444-444444444444"] == "I-2"
    assert mapping["33333333-3333-3333-3333-333333333333"] == "II-1"
    assert mapping["11111111-1111-1111-1111-111111111111"] == "III-1"


def test_unknown_generation_and_missing_y_fall_back_to_question_mark_label() -> None:
    detail: dict[str, Any] = {
        "individuals": [
            {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "display_name": "Alice"},
            {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "display_name": "Bob"},
        ]
    }

    mapping = build_label_mapping(detail, LabelStyle.GENERATION_NUMBER)

    assert mapping["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"] == "?-1"
    assert mapping["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"] == "?-2"
