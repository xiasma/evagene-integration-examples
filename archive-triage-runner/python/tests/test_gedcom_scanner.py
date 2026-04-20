from pathlib import Path

import pytest

from archive_triage.gedcom_scanner import GedcomScanner, ScannerError


def test_yields_ged_files_in_sorted_order(tmp_path: Path) -> None:
    (tmp_path / "b.ged").write_text("B", encoding="utf-8")
    (tmp_path / "a.ged").write_text("A", encoding="utf-8")

    files = list(GedcomScanner(tmp_path).scan())

    assert [f.path.name for f in files] == ["a.ged", "b.ged"]
    assert files[0].content == "A"
    assert files[1].content == "B"


def test_walks_subdirectories(tmp_path: Path) -> None:
    nested = tmp_path / "archive-2019"
    nested.mkdir()
    (nested / "family.ged").write_text("nested", encoding="utf-8")

    files = list(GedcomScanner(tmp_path).scan())

    assert len(files) == 1
    assert files[0].path.name == "family.ged"


def test_skips_non_ged_files(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    (tmp_path / "a.ged").write_text("A", encoding="utf-8")

    files = list(GedcomScanner(tmp_path).scan())

    assert [f.path.name for f in files] == ["a.ged"]


def test_missing_directory_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    with pytest.raises(ScannerError, match="not a directory"):
        list(GedcomScanner(missing).scan())
