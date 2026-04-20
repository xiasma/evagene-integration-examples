import io

from archive_triage.csv_writer import HEADER, CsvWriter
from archive_triage.row_result import RowResult


def _write(rows: list[RowResult]) -> str:
    sink = io.StringIO()
    CsvWriter(sink).write(rows)
    return sink.getvalue()


def test_writes_header_first() -> None:
    output = _write([])

    assert output.splitlines()[0] == ",".join(HEADER)


def test_formats_successful_row_with_true_refer_flag() -> None:
    row = RowResult(
        pedigree_id="pedigree-1",
        proband_name="Jane Doe",
        category="high",
        refer_for_genetics=True,
        triggers_matched_count=2,
        error="",
    )

    lines = _write([row]).splitlines()

    assert lines[1] == "pedigree-1,Jane Doe,high,true,2,"


def test_formats_failure_row_with_empty_bool_and_quoted_error() -> None:
    row = RowResult(
        pedigree_id="",
        proband_name="family",
        category="",
        refer_for_genetics=None,
        triggers_matched_count=0,
        error="create_pedigree failed: HTTP 503",
    )

    lines = _write([row]).splitlines()

    assert lines[1] == ',family,,,0,create_pedigree failed: HTTP 503'


def test_quotes_commas_inside_names() -> None:
    row = RowResult(
        pedigree_id="pedigree-1",
        proband_name="Doe, Jane",
        category="moderate",
        refer_for_genetics=False,
        triggers_matched_count=1,
        error="",
    )

    lines = _write([row]).splitlines()

    assert '"Doe, Jane"' in lines[1]
