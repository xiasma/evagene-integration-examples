import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { type TextSink, present } from '../src/presenter.js';
import type { TrafficLightReport } from '../src/trafficLight.js';

class CapturingSink implements TextSink {
  private buffer = '';

  write(text: string): void {
    this.buffer += text;
  }

  value(): string {
    return this.buffer;
  }
}

function report(triggers: readonly string[]): TrafficLightReport {
  return {
    colour: 'RED',
    headline: 'High risk for Jane Doe \u2014 refer for genetics assessment.',
    outcome: {
      counseleeName: 'Jane Doe',
      category: 'high',
      referForGeneticsAssessment: true,
      triggers,
      notes: [],
    },
  };
}

test('writes colour label and headline on the first line', () => {
  const sink = new CapturingSink();
  present(report([]), sink);

  const firstLine = sink.value().split('\n')[0] ?? '';
  ok(firstLine.startsWith('RED'));
  ok(firstLine.includes('Jane Doe'));
});

test('writes each trigger on its own indented line', () => {
  const sink = new CapturingSink();
  present(report(['Trigger A', 'Trigger B']), sink);

  const lines = sink.value().split('\n');
  strictEqual(lines[1], '  - Trigger A');
  strictEqual(lines[2], '  - Trigger B');
});

test('writes only the headline when no triggers', () => {
  const sink = new CapturingSink();
  present(report([]), sink);

  ok(!sink.value().includes('  - '));
});
