import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { NiceOutcome, RiskCategory } from '../src/classifier.js';
import { toTrafficLight } from '../src/trafficLight.js';

function outcome(category: RiskCategory): NiceOutcome {
  return {
    counseleeName: 'Jane Doe',
    category,
    referForGeneticsAssessment: category !== 'near_population',
    triggers: [],
    notes: [],
  };
}

test('near_population is GREEN', () => {
  strictEqual(toTrafficLight(outcome('near_population')).colour, 'GREEN');
});

test('moderate is AMBER', () => {
  strictEqual(toTrafficLight(outcome('moderate')).colour, 'AMBER');
});

test('high is RED', () => {
  strictEqual(toTrafficLight(outcome('high')).colour, 'RED');
});

test('headline contains counselee name', () => {
  ok(toTrafficLight(outcome('moderate')).headline.includes('Jane Doe'));
});

test('headline falls back when counselee name is empty', () => {
  const report = toTrafficLight({
    counseleeName: '',
    category: 'high',
    referForGeneticsAssessment: true,
    triggers: [],
    notes: [],
  });
  ok(report.headline.includes('counselee'));
});
