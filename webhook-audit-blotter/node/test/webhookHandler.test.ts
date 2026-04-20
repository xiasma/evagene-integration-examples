import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { test } from 'node:test';

import type { AppendArgs } from '../src/eventStore.js';
import { WebhookHandler } from '../src/webhookHandler.js';

const SECRET = 'shared-secret';
const FIXED_NOW = '2026-04-20T09:15:22Z';

class RecordingStore {
  readonly appended: AppendArgs[] = [];
  append(args: AppendArgs): number {
    this.appended.push(args);
    return this.appended.length;
  }
}

function sign(body: Buffer, secret = SECRET): string {
  return `sha256=${createHmac('sha256', secret).update(body).digest('hex')}`;
}

function handler(store: RecordingStore): WebhookHandler {
  return new WebhookHandler({ secret: SECRET, store, clock: { nowIso: () => FIXED_NOW } });
}

test('valid signature and JSON body: appends and returns accepted', () => {
  const body = Buffer.from('{"event":"pedigree.updated"}', 'utf8');
  const store = new RecordingStore();

  const outcome = handler(store).handle({
    rawBody: body,
    signatureHeader: sign(body),
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'accepted');
  strictEqual(store.appended.length, 1);
  deepStrictEqual(store.appended[0], {
    receivedAt: FIXED_NOW,
    eventType: 'pedigree.updated',
    body: body.toString('utf8'),
  });
});

test('bad signature: returns bad_signature and does not append', () => {
  const body = Buffer.from('{"event":"pedigree.updated"}', 'utf8');
  const store = new RecordingStore();

  const outcome = handler(store).handle({
    rawBody: body,
    signatureHeader: sign(body, 'wrong-secret'),
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'bad_signature');
  strictEqual(store.appended.length, 0);
});

test('missing signature header: rejected as bad_signature', () => {
  const body = Buffer.from('{"event":"pedigree.updated"}', 'utf8');
  const store = new RecordingStore();

  const outcome = handler(store).handle({
    rawBody: body,
    signatureHeader: undefined,
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'bad_signature');
});

test('non-JSON body: bad_request and nothing stored', () => {
  const body = Buffer.from('not-json', 'utf8');
  const store = new RecordingStore();

  const outcome = handler(store).handle({
    rawBody: body,
    signatureHeader: sign(body),
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'bad_request');
  strictEqual(store.appended.length, 0);
});

test('JSON array (not an object) is also rejected as bad_request', () => {
  const body = Buffer.from('[1,2,3]', 'utf8');
  const store = new RecordingStore();

  const outcome = handler(store).handle({
    rawBody: body,
    signatureHeader: sign(body),
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'bad_request');
});

test('missing event header: rejected as bad_request', () => {
  const body = Buffer.from('{"ok":true}', 'utf8');
  const store = new RecordingStore();

  const outcome = handler(store).handle({
    rawBody: body,
    signatureHeader: sign(body),
    eventTypeHeader: undefined,
  });

  strictEqual(outcome.status, 'bad_request');
});
