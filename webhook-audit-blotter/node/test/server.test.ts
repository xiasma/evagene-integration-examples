import { strictEqual } from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { EventStore } from '../src/eventStore.js';
import { buildServer } from '../src/server.js';
import { WebhookHandler } from '../src/webhookHandler.js';

const SECRET = 'integration-secret';
const FIXED_NOW = '2026-04-20T09:15:22Z';

async function withRunningServer(
  body: (port: number) => Promise<void>,
): Promise<void> {
  const dir = mkdtempSync(join(tmpdir(), 'blotter-int-'));
  const store = new EventStore(join(dir, 'test.db'));
  const handler = new WebhookHandler({
    secret: SECRET,
    store,
    clock: { nowIso: () => FIXED_NOW },
  });
  const app = buildServer({ handler, store });

  await new Promise<void>((resolve, reject) => {
    const server = app.listen(0, () => {
      const address = server.address();
      if (typeof address !== 'object' || address === null) {
        reject(new Error('Server did not bind to a port.'));
        return;
      }
      body(address.port)
        .then(() => {
          server.close(() => {
            store.close();
            rmSync(dir, { recursive: true, force: true });
            resolve();
          });
        })
        .catch((error: unknown) => {
          server.close(() => {
            store.close();
            rmSync(dir, { recursive: true, force: true });
            reject(error instanceof Error ? error : new Error(String(error)));
          });
        });
    });
  });
}

function sign(body: string): string {
  return `sha256=${createHmac('sha256', SECRET).update(body).digest('hex')}`;
}

test('round-trip: signed POST /webhook, then GET /events returns the row, then /events/verify says ok', async () => {
  await withRunningServer(async port => {
    const body = '{"event":"pedigree.updated","pedigree_id":"abc"}';

    const postResponse = await fetch(`http://127.0.0.1:${port.toString()}/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Evagene-Event': 'pedigree.updated',
        'X-Evagene-Signature-256': sign(body),
      },
      body,
    });
    strictEqual(postResponse.status, 204);

    const listResponse = await fetch(`http://127.0.0.1:${port.toString()}/events`);
    strictEqual(listResponse.status, 200);
    const lines = (await listResponse.text()).trim().split('\n').filter(Boolean);
    strictEqual(lines.length, 1);
    const row = JSON.parse(lines[0] ?? '{}') as { readonly eventType: string; readonly body: string };
    strictEqual(row.eventType, 'pedigree.updated');
    strictEqual(row.body, body);

    const verifyResponse = await fetch(`http://127.0.0.1:${port.toString()}/events/verify`);
    strictEqual(verifyResponse.status, 200);
    const verdict = (await verifyResponse.json()) as { readonly ok: boolean; readonly break_at: number | null };
    strictEqual(verdict.ok, true);
    strictEqual(verdict.break_at, null);
  });
});

test('wrong signature: /webhook returns 401 and nothing is stored', async () => {
  await withRunningServer(async port => {
    const body = '{"event":"pedigree.updated"}';
    const response = await fetch(`http://127.0.0.1:${port.toString()}/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Evagene-Event': 'pedigree.updated',
        'X-Evagene-Signature-256': 'sha256=' + 'a'.repeat(64),
      },
      body,
    });
    strictEqual(response.status, 401);

    const listResponse = await fetch(`http://127.0.0.1:${port.toString()}/events`);
    const text = (await listResponse.text()).trim();
    strictEqual(text, '');
  });
});

test('non-JSON body but valid signature: /webhook returns 400', async () => {
  await withRunningServer(async port => {
    const body = 'not-json';
    const response = await fetch(`http://127.0.0.1:${port.toString()}/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Evagene-Event': 'pedigree.updated',
        'X-Evagene-Signature-256': sign(body),
      },
      body,
    });
    strictEqual(response.status, 400);
  });
});
