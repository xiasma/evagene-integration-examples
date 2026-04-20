/**
 * SQLite-backed, hash-chained audit log.
 *
 * Each row's `row_hash` is SHA-256 over `prev_hash || received_at ||
 * event_type || body`, concatenated as UTF-8.  Re-running that
 * computation across every stored row reveals any subsequent edit: the
 * first row whose recomputed hash disagrees with its stored `row_hash`
 * (or whose stored `prev_hash` does not match the previous row's
 * `row_hash`) is returned as the break point.
 */

import { createHash } from 'node:crypto';

import Database, { type Database as SqliteDatabase } from 'better-sqlite3';

export interface AppendArgs {
  readonly receivedAt: string;
  readonly eventType: string;
  readonly body: string;
}

export interface EventRow {
  readonly id: number;
  readonly receivedAt: string;
  readonly eventType: string;
  readonly body: string;
  readonly prevHash: string;
  readonly rowHash: string;
}

export interface VerifyResult {
  readonly ok: boolean;
  readonly breakAt: number | null;
}

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    body        TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    row_hash    TEXT NOT NULL
  );
`;

export class EventStore {
  private readonly db: SqliteDatabase;

  constructor(path: string) {
    this.db = new Database(path);
    this.db.pragma('journal_mode = WAL');
    this.db.exec(SCHEMA);
  }

  append(args: AppendArgs): number {
    const prevHash = this.latestRowHash();
    const rowHash = hashChainEntry(prevHash, args);
    const result = this.db
      .prepare(
        `INSERT INTO events (received_at, event_type, body, prev_hash, row_hash)
         VALUES (?, ?, ?, ?, ?)`,
      )
      .run(args.receivedAt, args.eventType, args.body, prevHash, rowHash);
    return Number(result.lastInsertRowid);
  }

  list(limit: number, offset: number): EventRow[] {
    const rows = this.db
      .prepare(
        `SELECT id, received_at, event_type, body, prev_hash, row_hash
         FROM events ORDER BY id ASC LIMIT ? OFFSET ?`,
      )
      .all(limit, offset) as readonly {
      readonly id: number;
      readonly received_at: string;
      readonly event_type: string;
      readonly body: string;
      readonly prev_hash: string;
      readonly row_hash: string;
    }[];
    return rows.map(toEventRow);
  }

  verifyChain(): VerifyResult {
    const stmt = this.db.prepare(
      `SELECT id, received_at, event_type, body, prev_hash, row_hash
       FROM events ORDER BY id ASC`,
    );
    let expectedPrev = '';
    for (const raw of stmt.iterate() as IterableIterator<{
      readonly id: number;
      readonly received_at: string;
      readonly event_type: string;
      readonly body: string;
      readonly prev_hash: string;
      readonly row_hash: string;
    }>) {
      const recomputed = hashChainEntry(expectedPrev, {
        receivedAt: raw.received_at,
        eventType: raw.event_type,
        body: raw.body,
      });
      if (raw.prev_hash !== expectedPrev || raw.row_hash !== recomputed) {
        return { ok: false, breakAt: raw.id };
      }
      expectedPrev = raw.row_hash;
    }
    return { ok: true, breakAt: null };
  }

  close(): void {
    this.db.close();
  }

  private latestRowHash(): string {
    const row = this.db.prepare(`SELECT row_hash FROM events ORDER BY id DESC LIMIT 1`).get() as
      | { readonly row_hash: string }
      | undefined;
    return row?.row_hash ?? '';
  }
}

function hashChainEntry(prevHash: string, args: AppendArgs): string {
  return createHash('sha256')
    .update(prevHash, 'utf8')
    .update(args.receivedAt, 'utf8')
    .update(args.eventType, 'utf8')
    .update(args.body, 'utf8')
    .digest('hex');
}

function toEventRow(raw: {
  readonly id: number;
  readonly received_at: string;
  readonly event_type: string;
  readonly body: string;
  readonly prev_hash: string;
  readonly row_hash: string;
}): EventRow {
  return {
    id: raw.id,
    receivedAt: raw.received_at,
    eventType: raw.event_type,
    body: raw.body,
    prevHash: raw.prev_hash,
    rowHash: raw.row_hash,
  };
}
