import json
from pathlib import Path
from typing import Any

import pytest
from conftest import FIXTURES

from pedigree_diff.config import SnapshotSource
from pedigree_diff.snapshot_loader import (
    SnapshotFileError,
    SnapshotLoader,
    normalise_pedigree_detail,
)


class _StubFetcher:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[str] = []

    def get_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]:
        self.calls.append(pedigree_id)
        return self._payload


def _load_fixture(name: str) -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return parsed


def test_loads_from_json_file() -> None:
    source = SnapshotSource(
        raw=str(FIXTURES / "pedigree-t0.json"),
        pedigree_id=None,
        path=str(FIXTURES / "pedigree-t0.json"),
    )

    snapshot = SnapshotLoader(fetcher=None).load(source)

    assert snapshot.display_name == "Smith BRCA Family"
    assert len(snapshot.individuals) == 8


def test_loads_from_uuid_via_fetcher() -> None:
    payload = _load_fixture("pedigree-t0.json")
    fetcher = _StubFetcher(payload)
    source = SnapshotSource(
        raw="11111111-1111-1111-1111-111111111111",
        pedigree_id="11111111-1111-1111-1111-111111111111",
        path=None,
    )

    snapshot = SnapshotLoader(fetcher=fetcher).load(source)

    assert fetcher.calls == ["11111111-1111-1111-1111-111111111111"]
    assert snapshot.display_name == "Smith BRCA Family"


def test_uuid_source_without_fetcher_fails() -> None:
    source = SnapshotSource(
        raw="11111111-1111-1111-1111-111111111111",
        pedigree_id="11111111-1111-1111-1111-111111111111",
        path=None,
    )

    with pytest.raises(SnapshotFileError, match="no API client"):
        SnapshotLoader(fetcher=None).load(source)


def test_missing_file_raises_snapshot_file_error(tmp_path: Path) -> None:
    source = SnapshotSource(
        raw=str(tmp_path / "missing.json"),
        pedigree_id=None,
        path=str(tmp_path / "missing.json"),
    )

    with pytest.raises(SnapshotFileError, match="Cannot read"):
        SnapshotLoader(fetcher=None).load(source)


def test_malformed_json_raises_snapshot_file_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ not: json", encoding="utf-8")
    source = SnapshotSource(raw=str(path), pedigree_id=None, path=str(path))

    with pytest.raises(SnapshotFileError, match="not valid JSON"):
        SnapshotLoader(fetcher=None).load(source)


def test_top_level_non_object_raises(tmp_path: Path) -> None:
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")
    source = SnapshotSource(raw=str(path), pedigree_id=None, path=str(path))

    with pytest.raises(SnapshotFileError, match="JSON object"):
        SnapshotLoader(fetcher=None).load(source)


def test_normalise_extracts_date_of_birth_from_birth_event() -> None:
    snapshot = normalise_pedigree_detail(_load_fixture("pedigree-t0.json"))

    emma = next(i for i in snapshot.individuals if i.display_name == "Emma Smith")
    assert emma.date_of_birth == "1985-07-05"


def test_normalise_detects_proband_from_nonzero_proband_field() -> None:
    snapshot = normalise_pedigree_detail(_load_fixture("pedigree-t0.json"))

    assert snapshot.proband_id == "55555555-5555-5555-5555-555555555555"


def test_normalise_builds_parent_child_links() -> None:
    snapshot = normalise_pedigree_detail(_load_fixture("pedigree-t0.json"))

    parent_ids = {link.parent_id for link in snapshot.parent_child_links}
    # Emma's parents: Robert and Anna
    assert "33333333-3333-3333-3333-333333333333" in parent_ids
    assert "44444444-4444-4444-4444-444444444444" in parent_ids


def test_normalise_builds_partner_links() -> None:
    snapshot = normalise_pedigree_detail(_load_fixture("pedigree-t0.json"))

    # George + Helen, Frank + Susan, Robert + Anna: three pairings.
    assert len(snapshot.partner_links) == 3
