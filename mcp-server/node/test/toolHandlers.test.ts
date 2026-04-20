import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { TOOL_SPECS, ToolArgumentError, handleCall } from '../src/toolHandlers.js';

import { FakeClient } from './fakes.js';

const PEDIGREE_ID = '3d7b9b2e-4f3a-4b2d-9a1c-2e0a2b3c4d5e';
const PROBAND_ID = '11111111-1111-1111-1111-111111111111';

test('every tool has a JSON schema', () => {
  for (const spec of TOOL_SPECS) {
    strictEqual((spec.inputSchema as Record<string, unknown>).type, 'object');
  }
});

test('list_pedigrees summarises items', async () => {
  const client = new FakeClient();
  client.listPedigreesResult = [
    {
      id: PEDIGREE_ID,
      display_name: 'BRCA family',
      date_represented: '2024-06-01',
      disease_ids: ['d1'],
      owner: 'user-1',
    },
  ];

  const result = await handleCall(client, 'list_pedigrees', {});

  deepStrictEqual(result, [
    {
      id: PEDIGREE_ID,
      display_name: 'BRCA family',
      date_represented: '2024-06-01',
      disease_ids: ['d1'],
    },
  ]);
});

test('describe_pedigree wraps text', async () => {
  const client = new FakeClient();
  client.describePedigreeResult = 'A two-generation family...';

  const result = await handleCall(client, 'describe_pedigree', { pedigree_id: PEDIGREE_ID });

  deepStrictEqual(result, {
    pedigree_id: PEDIGREE_ID,
    description: 'A two-generation family...',
  });
});

test('calculate_risk passes model and counselee', async () => {
  const client = new FakeClient();

  await handleCall(client, 'calculate_risk', {
    pedigree_id: PEDIGREE_ID,
    model: 'NICE',
    counselee_id: PROBAND_ID,
  });

  deepStrictEqual(client.calls[0], [
    'calculateRisk',
    { pedigreeId: PEDIGREE_ID, model: 'NICE', counseleeId: PROBAND_ID },
  ]);
});

test('calculate_risk requires model', async () => {
  const client = new FakeClient();

  await rejects(
    () => handleCall(client, 'calculate_risk', { pedigree_id: PEDIGREE_ID }),
    ToolArgumentError,
  );
});

test('add_individual creates and attaches', async () => {
  const client = new FakeClient();
  client.createIndividualResult = { id: PROBAND_ID, display_name: 'Proband' };

  const result = await handleCall(client, 'add_individual', {
    pedigree_id: PEDIGREE_ID,
    display_name: 'Proband',
    biological_sex: 'female',
  });

  const resultObj = result as { pedigree_id: string; individual: { id: string } };
  strictEqual(resultObj.pedigree_id, PEDIGREE_ID);
  strictEqual(resultObj.individual.id, PROBAND_ID);
  deepStrictEqual(
    client.calls.map(([name]) => name),
    ['createIndividual', 'addIndividualToPedigree'],
  );
});

test('add_relative passes kinship fields', async () => {
  const client = new FakeClient();

  await handleCall(client, 'add_relative', {
    pedigree_id: PEDIGREE_ID,
    relative_of: PROBAND_ID,
    relative_type: 'sister',
    display_name: 'Jane',
    biological_sex: 'female',
  });

  deepStrictEqual(client.calls[0], [
    'addRelative',
    {
      pedigreeId: PEDIGREE_ID,
      relativeOf: PROBAND_ID,
      relativeType: 'sister',
      displayName: 'Jane',
      biologicalSex: 'female',
    },
  ]);
});

test('unknown tool raises', async () => {
  const client = new FakeClient();

  await rejects(() => handleCall(client, 'does_not_exist', {}), ToolArgumentError);
});
