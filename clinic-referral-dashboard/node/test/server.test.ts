import { ok, strictEqual } from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import type { EvageneApi, PedigreeSummary } from '../src/evageneClient.js';
import { EventStore } from '../src/eventStore.js';
import { buildServer } from '../src/server.js';
import { SseBroker } from '../src/sseBroker.js';
import { WebhookHandler } from '../src/webhookHandler.js';

const SECRET = 'integration-secret';
const FIXED_NOW = '2026-04-20T09:15:22Z';
const PEDIGREE_ID = 'a1cfe665-3b2d-4f5e-9c1a-8d7e6f5a4b3c';

class StubEvagene implements EvageneApi {
  fetchEmbedSvg(): Promise<string> {
    return Promise.resolve('<svg xmlns="http://www.w3.org/2000/svg"></svg>');
  }
  calculateNice(): Promise<unknown> {
    return Promise.resolve({
      counselee_name: 'Jane',
      cancer_risk: { nice_category: 'moderate', nice_refer_genetics: false },
    });
  }
  getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary> {
    return Promise.resolve({ id: pedigreeId, displayName: 'Windsor family' });
  }
}

async function withRunningServer(body: (port: number) => Promise<void>): Promise<void> {
  const dir = mkdtempSync(join(tmpdir(), 'dashboard-int-'));
  const store = new EventStore(join(dir, 'test.db'));
  const broker = new SseBroker();
  const handler = new WebhookHandler({
    secret: SECRET,
    store,
    publisher: broker,
    clock: { nowIso: () => FIXED_NOW },
  });
  const app = buildServer({ handler, store, broker, evagene: new StubEvagene() });

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

async function postSignedWebhook(port: number, body: string, event: string): Promise<Response> {
  return fetch(`http://127.0.0.1:${port.toString()}/webhook`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Evagene-Event': event,
      'X-Evagene-Signature-256': sign(body),
    },
    body,
  });
}

test('round-trip: signed POST /webhook persists the row and /events/verify is ok', async () => {
  await withRunningServer(async port => {
    const body = JSON.stringify({ id: PEDIGREE_ID });
    const post = await postSignedWebhook(port, body, 'pedigree.created');
    strictEqual(post.status, 204);

    const list = await fetch(`http://127.0.0.1:${port.toString()}/events`);
    const lines = (await list.text()).trim().split('\n').filter(Boolean);
    strictEqual(lines.length, 1);

    const verify = await fetch(`http://127.0.0.1:${port.toString()}/events/verify`);
    const verdict = (await verify.json()) as { readonly ok: boolean; readonly break_at: number | null };
    strictEqual(verdict.ok, true);
    strictEqual(verdict.break_at, null);
  });
});

test('/events-stream receives a named webhook event after a signed POST', async () => {
  await withRunningServer(async port => {
    const streamResponse = await fetch(`http://127.0.0.1:${port.toString()}/events-stream`);
    ok(streamResponse.body, 'SSE response should have a body');
    strictEqual(streamResponse.headers.get('content-type'), 'text/event-stream');

    const reader = streamResponse.body.getReader();
    const readAllFrames = consumeUntilEventFrame(reader);

    // Give the server a beat to register the subscription before firing the webhook.
    await new Promise(resolve => setTimeout(resolve, 20));

    const body = JSON.stringify({ id: PEDIGREE_ID });
    strictEqual((await postSignedWebhook(port, body, 'pedigree.created')).status, 204);

    const frame = await readAllFrames;
    await reader.cancel();

    ok(frame.includes('event: webhook'), 'frame should carry the webhook event name');
    ok(frame.includes(`"eventType":"pedigree.created"`), 'frame should include the eventType');
    ok(frame.includes(PEDIGREE_ID), 'frame should include the pedigree id from the body');
  });
});

test('GET /pedigree-card/:id renders an SVG and a NICE category label', async () => {
  await withRunningServer(async port => {
    const response = await fetch(
      `http://127.0.0.1:${port.toString()}/pedigree-card/${PEDIGREE_ID}`,
    );
    strictEqual(response.status, 200);
    const html = await response.text();
    ok(html.includes('<svg'), 'card should embed the SVG');
    ok(html.includes('Moderate risk'), 'card should include the NICE label');
    ok(html.includes('Windsor family'), 'card should include the pedigree display name');
  });
});

test('GET /pedigree-card/:id rejects a non-UUID id with 400', async () => {
  await withRunningServer(async port => {
    const response = await fetch(`http://127.0.0.1:${port.toString()}/pedigree-card/not-a-uuid`);
    strictEqual(response.status, 400);
  });
});

test('GET / returns the dashboard HTML', async () => {
  await withRunningServer(async port => {
    const response = await fetch(`http://127.0.0.1:${port.toString()}/`);
    strictEqual(response.status, 200);
    const html = await response.text();
    ok(html.includes('Clinic triage dashboard'));
    ok(html.includes('/events-stream'));
  });
});

test('GET /healthz returns ok', async () => {
  await withRunningServer(async port => {
    const response = await fetch(`http://127.0.0.1:${port.toString()}/healthz`);
    strictEqual(response.status, 200);
    strictEqual((await response.text()).trim(), 'ok');
  });
});

async function consumeUntilEventFrame(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): Promise<string> {
  const decoder = new TextDecoder();
  let buffer = '';
  const deadline = Date.now() + 2_000;
  while (Date.now() < deadline) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frameIndex = buffer.indexOf('event: webhook');
    if (frameIndex >= 0) {
      // Return the rest of the buffer from the frame start onward so the
      // assertions can inspect the full frame payload.
      return buffer.slice(frameIndex);
    }
  }
  throw new Error(`SSE frame not received before timeout; buffer was: ${JSON.stringify(buffer)}`);
}
