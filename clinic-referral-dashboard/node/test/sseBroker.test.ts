import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { SseBroker, type DashboardEvent } from '../src/sseBroker.js';

function sampleEvent(id: number): DashboardEvent {
  return {
    id,
    eventType: 'pedigree.created',
    receivedAt: '2026-04-20T00:00:00Z',
    body: `{"id":${id.toString()}}`,
  };
}

test('a subscriber receives every event published after it subscribes', () => {
  const broker = new SseBroker();
  const received: DashboardEvent[] = [];
  broker.subscribe(event => {
    received.push(event);
  });

  broker.publish(sampleEvent(1));
  broker.publish(sampleEvent(2));

  deepStrictEqual(received, [sampleEvent(1), sampleEvent(2)]);
});

test('multiple subscribers each receive the same events', () => {
  const broker = new SseBroker();
  const a: DashboardEvent[] = [];
  const b: DashboardEvent[] = [];
  broker.subscribe(event => {
    a.push(event);
  });
  broker.subscribe(event => {
    b.push(event);
  });

  broker.publish(sampleEvent(1));

  deepStrictEqual(a, [sampleEvent(1)]);
  deepStrictEqual(b, [sampleEvent(1)]);
});

test('a late subscriber only sees events published after it joins', () => {
  const broker = new SseBroker();
  const early: DashboardEvent[] = [];
  const late: DashboardEvent[] = [];
  broker.subscribe(event => {
    early.push(event);
  });

  broker.publish(sampleEvent(1));

  broker.subscribe(event => {
    late.push(event);
  });

  broker.publish(sampleEvent(2));

  deepStrictEqual(early, [sampleEvent(1), sampleEvent(2)]);
  deepStrictEqual(late, [sampleEvent(2)]);
});

test('unsubscribing stops further deliveries to that subscriber', () => {
  const broker = new SseBroker();
  const received: DashboardEvent[] = [];
  const unsubscribe = broker.subscribe(event => {
    received.push(event);
  });

  broker.publish(sampleEvent(1));
  unsubscribe();
  broker.publish(sampleEvent(2));

  deepStrictEqual(received, [sampleEvent(1)]);
  strictEqual(broker.size, 0);
});
