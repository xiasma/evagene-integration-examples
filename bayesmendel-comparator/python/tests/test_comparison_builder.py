import pytest

from bayesmendel_comparator.comparison_builder import (
    ResponseSchemaError,
    build_comparison,
)
from tests.fixtures_loader import load_all_fixtures


def test_one_row_per_model_in_registry_order() -> None:
    table = build_comparison(load_all_fixtures())

    assert len(table.rows) == 3
    assert [row["Model"] for row in table.rows] == ["BRCAPRO", "MMRpro", "PancPRO"]


def test_columns_include_fixed_and_lifetime() -> None:
    table = build_comparison(load_all_fixtures())

    assert table.columns[0] == "Model"
    assert table.columns[1] == "Counselee"
    assert table.columns[2] == "Any carrier"
    assert table.columns[-1] == "Lifetime risk @max-age"


def test_gene_columns_unioned_in_first_seen_order() -> None:
    table = build_comparison(load_all_fixtures())

    gene_cols = [
        col
        for col in table.columns
        if col not in {"Model", "Counselee", "Any carrier", "Lifetime risk @max-age"}
    ]
    assert gene_cols == [
        "Pr(BRCA1 mutation)",
        "Pr(BRCA2 mutation)",
        "Pr(Both genes mutated)",
        "Pr(MLH1 mutation)",
        "Pr(MSH2 mutation)",
        "Pr(MSH6)",
    ]


def test_brcapro_row_has_brca1_and_no_mlh1() -> None:
    table = build_comparison(load_all_fixtures())

    brcapro = table.rows[0]
    assert brcapro["Pr(BRCA1 mutation)"] == 0.4239
    assert brcapro["Pr(MLH1 mutation)"] is None


def test_lifetime_summary_uses_oldest_age() -> None:
    table = build_comparison(load_all_fixtures())

    assert (
        table.rows[0]["Lifetime risk @max-age"]
        == "Breast Ca Risk 38.48%; Ovarian Ca Risk 28.46%"
    )


def test_missing_carrier_probabilities_raises() -> None:
    with pytest.raises(ResponseSchemaError):
        build_comparison({"BRCAPRO": {"counselee_name": "X"}})


def test_non_numeric_carrier_probability_raises() -> None:
    with pytest.raises(ResponseSchemaError):
        build_comparison(
            {
                "BRCAPRO": {
                    "counselee_name": "X",
                    "carrier_probabilities": {"Pr(BRCA1 mutation)": "oops"},
                    "future_risks": [],
                }
            }
        )


def test_empty_payload_mapping_raises() -> None:
    with pytest.raises(ResponseSchemaError):
        build_comparison({})
