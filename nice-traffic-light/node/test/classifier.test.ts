import { deepStrictEqual, strictEqual, throws } from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { ResponseSchemaError, classifyNiceResponse } from '../src/classifier.js';

const here = dirname(fileURLToPath(import.meta.url));
const fixturesDir = resolve(here, '..', '..', 'fixtures');

function fixture(name: string): unknown {
  return JSON.parse(readFileSync(resolve(fixturesDir, `${name}.json`), 'utf8')) as unknown;
}

test('near_population parses to enum with no triggers', () => {
  const outcome = classifyNiceResponse(fixture('near_population'));
  strictEqual(outcome.category, 'near_population');
  strictEqual(outcome.referForGeneticsAssessment, false);
  deepStrictEqual(outcome.triggers, []);
});

test('moderate exposes single trigger', () => {
  const outcome = classifyNiceResponse(fixture('moderate'));
  strictEqual(outcome.category, 'moderate');
  strictEqual(outcome.referForGeneticsAssessment, true);
  strictEqual(outcome.triggers.length, 1);
});

test('high exposes all triggers and refer flag', () => {
  const outcome = classifyNiceResponse(fixture('high'));
  strictEqual(outcome.category, 'high');
  strictEqual(outcome.referForGeneticsAssessment, true);
  strictEqual(outcome.triggers.length, 2);
});

test('missing cancer_risk block throws', () => {
  throws(() => classifyNiceResponse({ model: 'NICE' }), ResponseSchemaError);
});

test('unknown category throws', () => {
  throws(
    () =>
      classifyNiceResponse({
        cancer_risk: {
          nice_category: 'catastrophic',
          nice_refer_genetics: true,
          nice_triggers: [],
          notes: [],
        },
      }),
    ResponseSchemaError,
  );
});

test('non-string trigger throws', () => {
  throws(
    () =>
      classifyNiceResponse({
        cancer_risk: {
          nice_category: 'moderate',
          nice_refer_genetics: true,
          nice_triggers: ['ok', 42],
          notes: [],
        },
      }),
    ResponseSchemaError,
  );
});
