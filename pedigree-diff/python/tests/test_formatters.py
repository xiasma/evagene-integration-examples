import io
import json
from datetime import date, datetime

from conftest import FIXTURES

from pedigree_diff.diff_engine import diff_pedigrees
from pedigree_diff.formatters import (
    FormatOptions,
    JsonFormatter,
    MarkdownFormatter,
    TextFormatter,
)
from pedigree_diff.snapshot_loader import normalise_pedigree_detail

_FIXED_TODAY = date(2026, 4, 18)
_SINCE = datetime(2026, 4, 15)


def _load_and_diff() -> tuple[object, object, object]:
    before_raw = json.loads((FIXTURES / "pedigree-t0.json").read_text(encoding="utf-8"))
    after_raw = json.loads((FIXTURES / "pedigree-t1.json").read_text(encoding="utf-8"))
    before = normalise_pedigree_detail(before_raw)
    after = normalise_pedigree_detail(after_raw)
    return diff_pedigrees(before, after), before, after


def _normalise_whitespace(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def test_text_formatter_matches_golden_file() -> None:
    diff, before, after = _load_and_diff()
    sink = io.StringIO()
    options = FormatOptions(
        include_unchanged=False,
        since=_SINCE,
        use_colour=False,
        today=_FIXED_TODAY,
    )

    TextFormatter().render(diff, before, after, options, sink)  # type: ignore[arg-type]

    expected = (FIXTURES / "expected-diff.txt").read_text(encoding="utf-8")
    assert _normalise_whitespace(sink.getvalue()) == _normalise_whitespace(expected)


def test_markdown_formatter_matches_golden_file() -> None:
    diff, before, after = _load_and_diff()
    sink = io.StringIO()
    options = FormatOptions(
        include_unchanged=False,
        since=_SINCE,
        use_colour=False,
        today=_FIXED_TODAY,
    )

    MarkdownFormatter().render(diff, before, after, options, sink)  # type: ignore[arg-type]

    expected = (FIXTURES / "expected-diff.md").read_text(encoding="utf-8")
    assert _normalise_whitespace(sink.getvalue()) == _normalise_whitespace(expected)


def test_json_formatter_matches_golden_file() -> None:
    diff, before, after = _load_and_diff()
    sink = io.StringIO()
    options = FormatOptions(
        include_unchanged=False,
        since=_SINCE,
        use_colour=False,
        today=_FIXED_TODAY,
    )

    JsonFormatter().render(diff, before, after, options, sink)  # type: ignore[arg-type]

    expected = json.loads((FIXTURES / "expected-diff.json").read_text(encoding="utf-8"))
    actual = json.loads(sink.getvalue())
    assert actual == expected


def test_json_output_is_byte_stable_across_runs() -> None:
    diff, before, after = _load_and_diff()
    options = FormatOptions(
        include_unchanged=False,
        since=None,
        use_colour=False,
        today=_FIXED_TODAY,
    )

    first = io.StringIO()
    second = io.StringIO()
    JsonFormatter().render(diff, before, after, options, first)  # type: ignore[arg-type]
    JsonFormatter().render(diff, before, after, options, second)  # type: ignore[arg-type]

    assert first.getvalue() == second.getvalue()


def test_text_formatter_colour_codes_appear_when_enabled() -> None:
    diff, before, after = _load_and_diff()
    sink = io.StringIO()
    options = FormatOptions(
        include_unchanged=False,
        since=None,
        use_colour=True,
        today=_FIXED_TODAY,
    )

    TextFormatter().render(diff, before, after, options, sink)  # type: ignore[arg-type]

    assert "\x1b[" in sink.getvalue()


def test_include_unchanged_is_honoured_in_text() -> None:
    diff, before, after = _load_and_diff()
    sink = io.StringIO()
    options = FormatOptions(
        include_unchanged=True,
        since=None,
        use_colour=False,
        today=_FIXED_TODAY,
    )

    TextFormatter().render(diff, before, after, options, sink)  # type: ignore[arg-type]

    assert "Unchanged:" in sink.getvalue()


def test_include_unchanged_is_honoured_in_json() -> None:
    diff, before, after = _load_and_diff()
    sink = io.StringIO()
    options = FormatOptions(
        include_unchanged=True,
        since=None,
        use_colour=False,
        today=_FIXED_TODAY,
    )

    JsonFormatter().render(diff, before, after, options, sink)  # type: ignore[arg-type]

    document = json.loads(sink.getvalue())
    assert "unchanged" in document
    assert len(document["unchanged"]) > 0


def test_no_changes_prints_no_changes_line() -> None:
    diff, before, _ = _load_and_diff()
    # Diff against itself is empty.
    self_diff = diff_pedigrees(before, before)  # type: ignore[arg-type]
    sink = io.StringIO()
    options = FormatOptions(
        include_unchanged=False,
        since=None,
        use_colour=False,
        today=_FIXED_TODAY,
    )

    TextFormatter().render(self_diff, before, before, options, sink)  # type: ignore[arg-type]

    assert "No changes." in sink.getvalue()
    assert not self_diff.has_changes()
    # quiet the "diff" unused warning.
    assert diff is not None
