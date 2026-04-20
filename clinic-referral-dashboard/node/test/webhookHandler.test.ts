import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { test } from 'node:test';

import type { AppendArgs, EventRow } from '../src/eventStore.js';
import type { DashboardEvent, EventPublisher } from '../src/sseBroker.js';
import { WebhookHandler } from '../src/webhookHandler.js';

const SECRET = 'shared-secret';
const FIXED_NOW = '2026-04-20T09:15:22Z';

class RecordingStore {
  readonly appended: AppendArgs[] = [];
  append(args: AppendArgs): EventRow {
    this.appended.push(args);
    return {
      id: this.appended.length,
      receivedAt: args.receivedAt,
      eventType: args.eventType,
      body: args.body,
      prevHash: '',
      rowHash: 'hash',
    };
  }
}

class RecordingPublisher implements EventPublisher {
  readonly published: DashboardEvent[] = [];
  publish(event: DashboardEvent): void {
    this.published.push(event);
  }
}

function sign(body: Buffer, secret = SECRET): string {
  return `sha256=${createHmac('sha256', secret).update(body).digest('hex')}`;
}

function build(): { handler: WebhookHandler; store: RecordingStore; publisher: RecordingPublisher } {
  const store = new RecordingStore();
  const publisher = new RecordingPublisher();
  const handler = new WebhookHandler({
    secret: SECRET,
    store,
    publisher,
    clock: { nowIso: () => FIXED_NOW },
  });
  return { handler, store, publisher };
}

test('valid signature: appends, publishes to SSE broker, returns accepted', () => {
  const body = Buffer.from('{"event":"pedigree.created"}', 'utf8');
  const { handler, store, publisher } = build();

  const outcome = handler.handle({
    rawBody: body,
    signatureHeader: sign(body),
    eventTypeHeader: 'pedigree.created',
  });

  strictEqual(outcome.status, 'accepted');
  strictEqual(store.appended.length, 1);
  deepStrictEqual(store.appended[0], {
    receivedAt: FIXED_NOW,
    eventType: 'pedigree.created',
    body: body.toString('utf8'),
  });
  strictEqual(publisher.published.length, 1);
  strictEqual(publisher.published[0]?.eventType, 'pedigree.created');
  strictEqual(publisher.published[0]?.body, body.toString('utf8'));
});

test('bad signature: no append, no publish, returns bad_signature', () => {
  const body = Buffer.from('{"event":"pedigree.updated"}', 'utf8');
  const { handler, store, publisher } = build();

  const outcome = handler.handle({
    rawBody: body,
    signatureHeader: sign(body, 'wrong-secret'),
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'bad_signature');
  strictEqual(store.appended.length, 0);
  strictEqual(publisher.published.length, 0);
});

test('missing signature header: rejected as bad_signature', () => {
  const body = Buffer.from('{"event":"pedigree.updated"}', 'utf8');
  const { handler, publisher } = build();

  const outcome = handler.handle({
    rawBody: body,
    signatureHeader: undefined,
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'bad_signature');
  strictEqual(publisher.published.length, 0);
});

test('non-JSON body: bad_request and nothing stored or published', () => {
  const body = Buffer.from('not-json', 'utf8');
  const { handler, store, publisher } = build();

  const outcome = handler.handle({
    rawBody: body,
    signatureHeader: sign(body),
    eventTypeHeader: 'pedigree.updated',
  });

  strictEqual(outcome.status, 'bad_request');
  strictEqual(store.appended.length, 0);
  strictEqual(publisher.published.length, 0);
});

test('missing event header: rejected as bad_request', () => {
  const body = Buffer.from('{"ok":true}', 'utf8');
  const { handler, publisher } = build();

  const outcome = handler.handle({
    rawBody: body,
    signatureHeader: sign(body),
    eventTypeHeader: undefined,
  });

  strictEqual(outcome.status, 'bad_request');
  strictEqual(publisher.published.length, 0);
});
