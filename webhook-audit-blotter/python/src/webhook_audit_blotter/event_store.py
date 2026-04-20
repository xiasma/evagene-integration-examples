"""SQLite-backed, hash-chained audit log.

Each row's ``row_hash`` is SHA-256 over
``prev_hash || received_at || event_type || body`` (UTF-8
concatenation).  Re-running that computation across every stored row
reveals any out-of-band edit: the first row whose recomputed hash
disagrees is returned as the break point.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from hashlib import sha256

_SCHEMA = """
    CREATE TABLE IF NOT EXISTS events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        received_at TEXT NOT NULL,
        event_type  TEXT NOT NULL,
        body        TEXT NOT NULL,
        prev_hash   TEXT NOT NULL,
        row_hash    TEXT NOT NULL
    );
"""


@dataclass(frozen=True)
class AppendArgs:
    received_at: str
    event_type: str
    body: str


@dataclass(frozen=True)
class EventRow:
    id: int
    received_at: str
    event_type: str
    body: str
    prev_hash: str
    row_hash: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    break_at: int | None


class EventStore:
    def __init__(self, path: str) -> None:
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.executescript(_SCHEMA)

    def append(self, args: AppendArgs) -> int:
        prev_hash = self._latest_row_hash()
        row_hash = _hash_chain_entry(prev_hash, args)
        cursor = self._connection.execute(
            """
            INSERT INTO events (received_at, event_type, body, prev_hash, row_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (args.received_at, args.event_type, args.body, prev_hash, row_hash),
        )
        self._connection.commit()
        row_id = cursor.lastrowid
        if row_id is None:
            raise RuntimeError("SQLite did not return a row id for the inserted event.")
        return row_id

    def list(self, limit: int, offset: int) -> list[EventRow]:
        cursor = self._connection.execute(
            """
            SELECT id, received_at, event_type, body, prev_hash, row_hash
            FROM events ORDER BY id ASC LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [_to_event_row(row) for row in cursor.fetchall()]

    def verify_chain(self) -> VerifyResult:
        cursor = self._connection.execute(
            """
            SELECT id, received_at, event_type, body, prev_hash, row_hash
            FROM events ORDER BY id ASC
            """,
        )
        expected_prev = ""
        for raw in cursor:
            row = _to_event_row(raw)
            recomputed = _hash_chain_entry(
                expected_prev,
                AppendArgs(row.received_at, row.event_type, row.body),
            )
            if row.prev_hash != expected_prev or row.row_hash != recomputed:
                return VerifyResult(ok=False, break_at=row.id)
            expected_prev = row.row_hash
        return VerifyResult(ok=True, break_at=None)

    def close(self) -> None:
        self._connection.close()

    def _latest_row_hash(self) -> str:
        row = self._connection.execute(
            "SELECT row_hash FROM events ORDER BY id DESC LIMIT 1",
        ).fetchone()
        if row is None:
            return ""
        result: str = row[0]
        return result


def _hash_chain_entry(prev_hash: str, args: AppendArgs) -> str:
    payload = (prev_hash + args.received_at + args.event_type + args.body).encode("utf-8")
    return sha256(payload).hexdigest()


def _to_event_row(raw: tuple[int, str, str, str, str, str]) -> EventRow:
    return EventRow(
        id=raw[0],
        received_at=raw[1],
        event_type=raw[2],
        body=raw[3],
        prev_hash=raw[4],
        row_hash=raw[5],
    )
