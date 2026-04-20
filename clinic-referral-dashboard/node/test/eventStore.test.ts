import { strictEqual } from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import Database from 'better-sqlite3';

import { EventStore } from '../src/eventStore.js';

function tempDbPath(): { readonly path: string; cleanup: () => void } {
  const dir = mkdtempSync(join(tmpdir(), 'dashboard-'));
  const path = join(dir, 'test.db');
  return {
    path,
    cleanup: () => {
      rmSync(dir, { recursive: true, force: true });
    },
  };
}

function appendSample(store: EventStore, n = 1): void {
  for (let i = 1; i <= n; i += 1) {
    store.append({
      receivedAt: `2026-04-20T00:00:0${i.toString()}Z`,
      eventType: 'pedigree.created',
      body: `{"n":${i.toString()}}`,
    });
  }
}

test('append returns a row with incrementing ids', () => {
  const { path, cleanup } = tempDbPath();
  const store = new EventStore(path);
  try {
    const first = store.append({
      receivedAt: '2026-04-20T00:00:00Z',
      eventType: 'pedigree.created',
      body: '{}',
    });
    const second = store.append({
      receivedAt: '2026-04-20T00:00:01Z',
      eventType: 'pedigree.updated',
      body: '{}',
    });
    strictEqual(first.id, 1);
    strictEqual(second.id, 2);
  } finally {
    store.close();
    cleanup();
  }
});

test('first row has empty prev_hash; subsequent rows chain to the previous row_hash', () => {
  const { path, cleanup } = tempDbPath();
  const store = new EventStore(path);
  try {
    appendSample(store, 3);
    const rows = store.list(10, 0);
    strictEqual(rows[0]?.prevHash, '');
    strictEqual(rows[1]?.prevHash, rows[0]?.rowHash);
    strictEqual(rows[2]?.prevHash, rows[1]?.rowHash);
  } finally {
    store.close();
    cleanup();
  }
});

test('list honours limit and offset', () => {
  const { path, cleanup } = tempDbPath();
  const store = new EventStore(path);
  try {
    appendSample(store, 5);
    strictEqual(store.list(2, 0).length, 2);
    strictEqual(store.list(2, 3).length, 2);
    strictEqual(store.list(10, 4).length, 1);
  } finally {
    store.close();
    cleanup();
  }
});

test('verifyChain returns ok when the log is untouched', () => {
  const { path, cleanup } = tempDbPath();
  const store = new EventStore(path);
  try {
    appendSample(store, 3);
    const result = store.verifyChain();
    strictEqual(result.ok, true);
    strictEqual(result.breakAt, null);
  } finally {
    store.close();
    cleanup();
  }
});

test('verifyChain detects a row whose body was edited out-of-band', () => {
  const { path, cleanup } = tempDbPath();
  const store = new EventStore(path);
  try {
    appendSample(store, 3);
    store.close();

    const direct = new Database(path);
    direct.prepare('UPDATE events SET body = ? WHERE id = ?').run('{"tampered":true}', 2);
    direct.close();

    const reopened = new EventStore(path);
    try {
      const result = reopened.verifyChain();
      strictEqual(result.ok, false);
      strictEqual(result.breakAt, 2);
    } finally {
      reopened.close();
    }
  } finally {
    cleanup();
  }
});
