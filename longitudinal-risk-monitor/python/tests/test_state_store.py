import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from longitudinal_risk_monitor.state_store import (
    AppendEventArgs,
    StateStore,
    UpsertArgs,
)

_PEDIGREE_A = "11111111-1111-1111-1111-111111111111"
_PEDIGREE_B = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def db_path(tmp_path: Path) -> Iterator[str]:
    yield str(tmp_path / "state.db")


def test_get_state_returns_none_when_absent(db_path: str) -> None:
    store = StateStore(db_path)
    try:
        assert store.get_state(_PEDIGREE_A) is None
    finally:
        store.close()


def test_upsert_inserts_then_overwrites_same_pedigree(db_path: str) -> None:
    store = StateStore(db_path)
    try:
        store.upsert_state(
            UpsertArgs(_PEDIGREE_A, "near_population", (), "2026-04-20T00:00:00Z"),
        )
        store.upsert_state(
            UpsertArgs(
                _PEDIGREE_A,
                "moderate",
                ("Single first-degree relative with breast cancer <40.",),
                "2026-04-21T00:00:00Z",
            ),
        )
        state = store.get_state(_PEDIGREE_A)
        assert state is not None
        assert state.category == "moderate"
        assert state.triggers == ("Single first-degree relative with breast cancer <40.",)
        assert state.recorded_at == "2026-04-21T00:00:00Z"
    finally:
        store.close()


def test_append_event_and_filter_by_pedigree(db_path: str) -> None:
    store = StateStore(db_path)
    try:
        store.append_event(
            AppendEventArgs(
                _PEDIGREE_A,
                "near_population",
                "moderate",
                ("Single first-degree relative with breast cancer <40.",),
                (),
                "2026-04-20T00:00:00Z",
            ),
        )
        store.append_event(
            AppendEventArgs(
                _PEDIGREE_B, "moderate", "high", ("Second trigger",), (), "2026-04-20T00:00:01Z",
            ),
        )

        all_events = store.list_events(None)
        only_a = store.list_events(_PEDIGREE_A)

        assert len(all_events) == 2
        assert len(only_a) == 1
        assert only_a[0].pedigree_id == _PEDIGREE_A
        assert only_a[0].triggers_added == (
            "Single first-degree relative with breast cancer <40.",
        )
    finally:
        store.close()


def test_schema_is_idempotent_across_reopens(db_path: str) -> None:
    first = StateStore(db_path)
    first.upsert_state(UpsertArgs(_PEDIGREE_A, "near_population", (), "2026-04-20T00:00:00Z"))
    first.close()

    second = StateStore(db_path)
    try:
        state = second.get_state(_PEDIGREE_A)
        assert state is not None
        assert state.category == "near_population"
    finally:
        second.close()


def test_triggers_round_trip_preserves_order_and_content(db_path: str) -> None:
    store = StateStore(db_path)
    try:
        triggers = (
            "First-degree female relative with breast cancer <40.",
            "Two or more first-degree relatives with breast cancer <50.",
        )
        store.upsert_state(UpsertArgs(_PEDIGREE_A, "high", triggers, "2026-04-20T00:00:00Z"))
        state = store.get_state(_PEDIGREE_A)
        assert state is not None
        assert state.triggers == triggers
    finally:
        store.close()


def test_sql_uses_parameter_binding_not_interpolation(db_path: str) -> None:
    # An injection-style pedigree_id survives a round-trip unmodified;
    # that's only true if the INSERT uses a prepared statement.
    injection = "x'); DROP TABLE pedigree_nice_state; --"
    store = StateStore(db_path)
    try:
        store.upsert_state(UpsertArgs(injection, "near_population", (), "2026-04-20T00:00:00Z"))
        state = store.get_state(injection)
        assert state is not None
        with sqlite3.connect(db_path) as direct:
            cursor = direct.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pedigree_nice_state'",
            )
            assert cursor.fetchone() is not None
    finally:
        store.close()
