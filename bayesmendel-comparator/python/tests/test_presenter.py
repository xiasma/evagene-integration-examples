import io
import json

from bayesmendel_comparator.comparison_builder import build_comparison
from bayesmendel_comparator.presenter import (
    present_csv,
    present_json,
    present_table,
    presenter_for,
)
from tests.fixtures_loader import load_all_fixtures


def _render(presenter: object, *, format_name: str = "") -> str:
    sink = io.StringIO()
    # Allow passing either a function directly or a format name via presenter_for.
    chosen = presenter if format_name == "" else presenter_for(format_name)  # type: ignore[arg-type]
    chosen(build_comparison(load_all_fixtures()), sink)  # type: ignore[operator]
    return sink.getvalue()


def test_table_writes_header_and_one_row_per_model() -> None:
    lines = _render(present_table).splitlines()

    assert len(lines) == 4
    assert "Model" in lines[0]
    assert "BRCAPRO" in lines[1]
    assert "MMRpro" in lines[2]
    assert "PancPRO" in lines[3]


def test_table_renders_missing_cells_as_dash() -> None:
    pancpro_line = _render(present_table).splitlines()[3]

    # PancPRO does not populate the BRCA1 column -- it must show as "-".
    assert " - " in pancpro_line


def test_csv_emits_header_and_one_row_per_model() -> None:
    lines = _render(present_csv).splitlines()

    assert len(lines) == 4
    assert lines[0].split(",")[0] == "Model"
    assert lines[1].split(",")[0] == "BRCAPRO"


def test_csv_does_not_quote_normal_strings() -> None:
    output = _render(present_csv)

    assert '"BRCAPRO"' not in output


def test_json_round_trips_to_columns_and_rows() -> None:
    parsed = json.loads(_render(present_json))

    assert "columns" in parsed
    assert "rows" in parsed
    assert len(parsed["rows"]) == 3
    assert parsed["rows"][0]["Model"] == "BRCAPRO"


def test_json_keeps_numeric_probabilities_as_numbers() -> None:
    parsed = json.loads(_render(present_json))

    assert parsed["rows"][0]["Pr(BRCA1 mutation)"] == 0.4239


def test_presenter_for_dispatches_by_name() -> None:
    assert presenter_for("table") is present_table
    assert presenter_for("csv") is present_csv
    assert presenter_for("json") is present_json
