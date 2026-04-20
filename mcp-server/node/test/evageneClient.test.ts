import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';

import { ApiError, EvageneClient } from '../src/evageneClient.js';
import type { HttpGateway } from '../src/httpGateway.js';

import { RecordingGateway, stubResponse } from './fakes.js';

const FIXTURES = resolve(dirname(fileURLToPath(import.meta.url)), '../../fixtures');
const PEDIGREE_ID = '3d7b9b2e-4f3a-4b2d-9a1c-2e0a2b3c4d5e';
const COUNSELEE_ID = '11111111-1111-1111-1111-111111111111';

function loadFixture(name: string): unknown {
  return JSON.parse(readFileSync(resolve(FIXTURES, name), 'utf-8'));
}

function clientWith(gateway: HttpGateway): EvageneClient {
  return new EvageneClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    http: gateway,
  });
}

function firstCall(gateway: RecordingGateway): RecordingGateway['calls'][number] {
  const [call] = gateway.calls;
  if (call === undefined) {
    throw new Error('no calls recorded');
  }
  return call;
}

test('list_pedigrees hits /api/pedigrees and parses array', async () => {
  const gateway = new RecordingGateway(() =>
    stubResponse({ status: 200, jsonPayload: loadFixture('sample-list-pedigrees.json') }),
  );

  const result = await clientWith(gateway).listPedigrees();

  strictEqual(result.length, 2);
  const call = firstCall(gateway);
  strictEqual(call.method, 'GET');
  strictEqual(call.url, 'https://evagene.example/api/pedigrees');
  strictEqual(call.headers['X-API-Key'], 'evg_test');
});

test('describe_pedigree returns text body', async () => {
  const gateway = new RecordingGateway(() =>
    stubResponse({ status: 200, textPayload: 'A two-generation family...' }),
  );

  const result = await clientWith(gateway).describePedigree(PEDIGREE_ID);

  strictEqual(result, 'A two-generation family...');
  strictEqual(
    firstCall(gateway).url,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/describe`,
  );
});

test('calculate_risk sends model and counselee_id', async () => {
  const gateway = new RecordingGateway(() =>
    stubResponse({ status: 200, jsonPayload: loadFixture('sample-risk-nice.json') }),
  );

  await clientWith(gateway).calculateRisk({
    pedigreeId: PEDIGREE_ID,
    model: 'NICE',
    counseleeId: COUNSELEE_ID,
  });

  const call = firstCall(gateway);
  strictEqual(call.method, 'POST');
  strictEqual(call.url, `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/risk/calculate`);
  deepStrictEqual(call.body, { model: 'NICE', counselee_id: COUNSELEE_ID });
});

test('calculate_risk omits counselee when absent', async () => {
  const gateway = new RecordingGateway(() =>
    stubResponse({ status: 200, jsonPayload: loadFixture('sample-risk-nice.json') }),
  );

  await clientWith(gateway).calculateRisk({ pedigreeId: PEDIGREE_ID, model: 'NICE' });

  deepStrictEqual(firstCall(gateway).body, { model: 'NICE' });
});

test('add_relative posts to the register endpoint', async () => {
  const gateway = new RecordingGateway(() =>
    stubResponse({ status: 201, jsonPayload: loadFixture('sample-add-relative.json') }),
  );

  await clientWith(gateway).addRelative({
    pedigreeId: PEDIGREE_ID,
    relativeOf: COUNSELEE_ID,
    relativeType: 'sister',
    displayName: 'Jane',
    biologicalSex: 'female',
  });

  const call = firstCall(gateway);
  strictEqual(
    call.url,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/register/add-relative`,
  );
  deepStrictEqual(call.body, {
    relative_of: COUNSELEE_ID,
    relative_type: 'sister',
    display_name: 'Jane',
    biological_sex: 'female',
  });
});

test('raises ApiError on non-2xx', async () => {
  const gateway = new RecordingGateway(() => stubResponse({ status: 500 }));

  await rejects(() => clientWith(gateway).listPedigrees(), ApiError);
});
