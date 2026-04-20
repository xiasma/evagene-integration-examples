"""SQLite-backed baseline store and change-event log.

Two tables are managed here:

* ``pedigree_nice_state`` — the *last known* NICE category and trigger
  set per pedigree.  One row per pedigree (the pedigree UUID is the PK).
* ``nice_events`` — an append-only log of category/trigger changes,
  written when the orchestrator detects a delta.

All SQL uses parameter binding; no value is interpolated into a
statement.  ``CREATE TABLE IF NOT EXISTS`` makes opening an existing
store a no-op, so the schema migration is safe across re-runs.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

_SCHEMA = """
    CREATE TABLE IF NOT EXISTS pedigree_nice_state (
        pedigree_id  TEXT PRIMARY KEY,
        category     TEXT NOT NULL,
        triggers_json TEXT NOT NULL,
        recorded_at  TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS nice_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedigree_id           TEXT NOT NULL,
        old_category          TEXT NOT NULL,
        new_category          TEXT NOT NULL,
        triggers_added_json   TEXT NOT NULL,
        triggers_removed_json TEXT NOT NULL,
        recorded_at           TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_nice_events_pedigree
        ON nice_events(pedigree_id, recorded_at DESC);
"""


@dataclass(frozen=True)
class StoredState:
    pedigree_id: str
    category: str
    triggers: tuple[str, ...]
    recorded_at: str


@dataclass(frozen=True)
class StoredEvent:
    id: int
    pedigree_id: str
    old_category: str
    new_category: str
    triggers_added: tuple[str, ...]
    triggers_removed: tuple[str, ...]
    recorded_at: str


@dataclass(frozen=True)
class UpsertArgs:
    pedigree_id: str
    category: str
    triggers: tuple[str, ...]
    recorded_at: str


@dataclass(frozen=True)
class AppendEventArgs:
    pedigree_id: str
    old_category: str
    new_category: str
    triggers_added: tuple[str, ...]
    triggers_removed: tuple[str, ...]
    recorded_at: str


class StateStore:
    def __init__(self, path: str) -> None:
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.executescript(_SCHEMA)

    def get_state(self, pedigree_id: str) -> StoredState | None:
        row = self._connection.execute(
            """
            SELECT pedigree_id, category, triggers_json, recorded_at
            FROM pedigree_nice_state WHERE pedigree_id = ?
            """,
            (pedigree_id,),
        ).fetchone()
        if row is None:
            return None
        return _to_stored_state(row)

    def upsert_state(self, args: UpsertArgs) -> None:
        self._connection.execute(
            """
            INSERT INTO pedigree_nice_state
                (pedigree_id, category, triggers_json, recorded_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(pedigree_id) DO UPDATE SET
                category = excluded.category,
                triggers_json = excluded.triggers_json,
                recorded_at = excluded.recorded_at
            """,
            (
                args.pedigree_id,
                args.category,
                json.dumps(list(args.triggers)),
                args.recorded_at,
            ),
        )
        self._connection.commit()

    def append_event(self, args: AppendEventArgs) -> int:
        cursor = self._connection.execute(
            """
            INSERT INTO nice_events
                (pedigree_id, old_category, new_category,
                 triggers_added_json, triggers_removed_json, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                args.pedigree_id,
                args.old_category,
                args.new_category,
                json.dumps(list(args.triggers_added)),
                json.dumps(list(args.triggers_removed)),
                args.recorded_at,
            ),
        )
        self._connection.commit()
        row_id = cursor.lastrowid
        if row_id is None:
            raise RuntimeError("SQLite did not return a row id for the inserted event.")
        return row_id

    def list_events(self, pedigree_id: str | None) -> list[StoredEvent]:
        if pedigree_id is None:
            cursor = self._connection.execute(
                """
                SELECT id, pedigree_id, old_category, new_category,
                       triggers_added_json, triggers_removed_json, recorded_at
                FROM nice_events ORDER BY id ASC
                """,
            )
        else:
            cursor = self._connection.execute(
                """
                SELECT id, pedigree_id, old_category, new_category,
                       triggers_added_json, triggers_removed_json, recorded_at
                FROM nice_events WHERE pedigree_id = ? ORDER BY id ASC
                """,
                (pedigree_id,),
            )
        return [_to_stored_event(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self._connection.close()


def _to_stored_state(row: tuple[str, str, str, str]) -> StoredState:
    return StoredState(
        pedigree_id=row[0],
        category=row[1],
        triggers=_decode_str_tuple(row[2]),
        recorded_at=row[3],
    )


def _to_stored_event(row: tuple[int, str, str, str, str, str, str]) -> StoredEvent:
    return StoredEvent(
        id=row[0],
        pedigree_id=row[1],
        old_category=row[2],
        new_category=row[3],
        triggers_added=_decode_str_tuple(row[4]),
        triggers_removed=_decode_str_tuple(row[5]),
        recorded_at=row[6],
    )


def _decode_str_tuple(raw: str) -> tuple[str, ...]:
    decoded = json.loads(raw)
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise ValueError("triggers column did not decode to list[str].")
    return tuple(decoded)
