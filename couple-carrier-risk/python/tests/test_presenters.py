import io
import json

import pytest

from couple_carrier_risk.couple_risk_calculator import (
    INHERITANCE_AR,
    INHERITANCE_XLR,
    CoupleRow,
)
from couple_carrier_risk.presenters import (
    present_csv,
    present_json,
    present_table,
    presenter_for,
)


def _rows() -> tuple[CoupleRow, ...]:
    return (
        CoupleRow(
            disease_name="Sickle cell anaemia",
            inheritance_pattern=INHERITANCE_AR,
            carrier_frequency_a=0.07,
            carrier_frequency_b=0.05,
            api_couple_offspring_risk_a=0.001225,
            api_couple_offspring_risk_b=0.000625,
            cross_partner_offspring_risk=0.000875,
        ),
        CoupleRow(
            disease_name="Duchenne muscular dystrophy",
            inheritance_pattern=INHERITANCE_XLR,
            carrier_frequency_a=None,
            carrier_frequency_b=0.0001,
            api_couple_offspring_risk_a=None,
            api_couple_offspring_risk_b=0.000025,
            cross_partner_offspring_risk=0.000025,
        ),
    )


def _render(presenter: object) -> str:
    sink = io.StringIO()
    presenter(_rows(), sink)  # type: ignore[operator]
    return sink.getvalue()


def test_table_renders_header_plus_one_row_per_disease() -> None:
    lines = _render(present_table).splitlines()

    assert len(lines) == 3
    assert "Disease" in lines[0]
    assert "Sickle cell anaemia" in lines[1]
    assert "Duchenne muscular dystrophy" in lines[2]


def test_table_renders_missing_cells_as_dash() -> None:
    dmd_line = _render(present_table).splitlines()[2]

    # Partner A's CF is missing for DMD -> "-", not 0.
    assert " - " in dmd_line


def test_csv_header_and_row_count_match_table() -> None:
    lines = _render(present_csv).splitlines()

    assert len(lines) == 3
    assert lines[0].split(",")[0] == "Disease"
    assert lines[1].split(",")[0] == "Sickle cell anaemia"


def test_json_emits_columns_and_rows() -> None:
    parsed = json.loads(_render(present_json))

    assert parsed["columns"][0] == "Disease"
    assert len(parsed["rows"]) == 2
    assert parsed["rows"][0]["Disease"] == "Sickle cell anaemia"


def test_json_keeps_numbers_as_numbers_and_missing_as_null() -> None:
    parsed = json.loads(_render(present_json))

    assert parsed["rows"][0]["CF(A)"] == pytest.approx(0.07)
    assert parsed["rows"][1]["CF(A)"] is None


def test_presenter_for_dispatches_by_name() -> None:
    assert presenter_for("table") is present_table
    assert presenter_for("csv") is present_csv
    assert presenter_for("json") is present_json
