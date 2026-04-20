import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from webhook_audit_blotter.event_store import AppendArgs, EventStore


@pytest.fixture()
def db_path(tmp_path: Path) -> Iterator[str]:
    path = tmp_path / "test.db"
    yield str(path)


def _append_sample(store: EventStore, n: int = 1) -> None:
    for i in range(1, n + 1):
        store.append(
            AppendArgs(
                received_at=f"2026-04-20T00:00:0{i}Z",
                event_type="pedigree.updated",
                body=f'{{"n":{i}}}',
            ),
        )


def test_append_returns_inserted_row_id(db_path: str) -> None:
    store = EventStore(db_path)
    try:
        first = store.append(AppendArgs("2026-04-20T00:00:00Z", "pedigree.created", "{}"))
        second = store.append(AppendArgs("2026-04-20T00:00:01Z", "pedigree.updated", "{}"))
        assert first == 1
        assert second == 2
    finally:
        store.close()


def test_first_row_has_empty_prev_hash_subsequent_rows_chain(db_path: str) -> None:
    store = EventStore(db_path)
    try:
        _append_sample(store, 3)
        rows = store.list(10, 0)
        assert rows[0].prev_hash == ""
        assert rows[1].prev_hash == rows[0].row_hash
        assert rows[2].prev_hash == rows[1].row_hash
    finally:
        store.close()


def test_list_honours_limit_and_offset(db_path: str) -> None:
    store = EventStore(db_path)
    try:
        _append_sample(store, 5)
        assert len(store.list(2, 0)) == 2
        assert len(store.list(2, 3)) == 2
        assert len(store.list(10, 4)) == 1
    finally:
        store.close()


def test_verify_chain_returns_ok_when_log_untouched(db_path: str) -> None:
    store = EventStore(db_path)
    try:
        _append_sample(store, 3)
        result = store.verify_chain()
        assert result.ok is True
        assert result.break_at is None
    finally:
        store.close()


def test_verify_chain_detects_out_of_band_body_edit(db_path: str) -> None:
    store = EventStore(db_path)
    _append_sample(store, 3)
    store.close()

    with sqlite3.connect(db_path) as direct:
        direct.execute("UPDATE events SET body = ? WHERE id = ?", ('{"tampered":true}', 2))
        direct.commit()

    reopened = EventStore(db_path)
    try:
        result = reopened.verify_chain()
        assert result.ok is False
        assert result.break_at == 2
    finally:
        reopened.close()
