import json

from research_anonymiser.k_anonymity_estimator import KAnonymityEstimate
from research_anonymiser.presenter import render_json


def _sample_anonymised() -> dict:  # type: ignore[type-arg]
    return {
        "display_name": "Anonymised pedigree",
        "date_represented": "1980-01-01",
        "properties": {"clinic_reference": "X"},
        "individuals": [
            {
                "id": "a",
                "display_name": "I-1",
                "generation_label": "I",
                "biological_sex": "female",
                "proband": 0,
                "proband_text": "",
                "events": [
                    {"type": "birth", "date_start": "1950-01-01",
                     "date_end": "1950-01-01", "properties": {}}
                ],
                "diseases": [
                    {"disease_id": "BC", "affection_status": "affected", "manifestations": []}
                ],
                "properties": {},
            }
        ],
        "relationships": [],
        "eggs": [],
    }


def _sample_estimate() -> KAnonymityEstimate:
    return KAnonymityEstimate(k=1, bucket_count=1, smallest_bucket_key=("female", "1950", 1),
                              total_individuals=1)


def test_top_level_keys_are_emitted_in_declared_order() -> None:
    rendered = render_json(_sample_anonymised(), _sample_estimate())

    document = json.loads(rendered)
    assert list(document.keys()) == [
        "display_name",
        "date_represented",
        "properties",
        "individuals",
        "relationships",
        "eggs",
        "k_anonymity",
    ]


def test_individual_fields_are_emitted_in_declared_order() -> None:
    rendered = render_json(_sample_anonymised(), _sample_estimate())

    document = json.loads(rendered)
    assert list(document["individuals"][0].keys()) == [
        "id",
        "display_name",
        "generation_label",
        "biological_sex",
        "proband",
        "proband_text",
        "events",
        "diseases",
        "properties",
    ]


def test_two_renders_of_same_input_are_byte_identical() -> None:
    first = render_json(_sample_anonymised(), _sample_estimate())
    second = render_json(_sample_anonymised(), _sample_estimate())

    assert first == second


def test_render_ends_with_a_trailing_newline() -> None:
    rendered = render_json(_sample_anonymised(), _sample_estimate())

    assert rendered.endswith("\n")
