import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { FetchLike } from '../src/evageneClient.js';
import { EvageneClient, EvageneError } from '../src/evageneClient.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';

interface Call {
  readonly url: string;
  readonly init: RequestInit | undefined;
}

function recording(status: number, body: unknown): { calls: Call[]; fetch: FetchLike } {
  const calls: Call[] = [];
  const fetch: FetchLike = (url, init) => {
    calls.push({ url, init });
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
  };
  return { calls, fetch };
}

function clientWith(fetch: FetchLike): EvageneClient {
  return new EvageneClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    fetch,
  });
}

test('calls /api/pedigrees/{id}/summary with X-API-Key header', async () => {
  const recorder = recording(200, {
    pedigree_id: PEDIGREE_ID,
    name: 'BRCA illustrative family',
    proband: { name: 'Alice', sex: 'female', disease_count: 1, genetic_test_count: 0, id: 'x' },
    diseases_in_family: { 'Breast cancer': 2 },
  });

  const summary = await clientWith(recorder.fetch).getPedigreeSummary(PEDIGREE_ID);

  strictEqual(
    recorder.calls[0]?.url,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/summary`,
  );
  const headers = recorder.calls[0]?.init?.headers as Record<string, string>;
  strictEqual(headers['X-API-Key'], 'evg_test');
  strictEqual(summary.name, 'BRCA illustrative family');
  strictEqual(summary.probandName, 'Alice');
  deepStrictEqual(summary.diseases, ['Breast cancer']);
  strictEqual(summary.viewUrl, `https://evagene.example/pedigrees/${PEDIGREE_ID}`);
});

test('handles pedigrees with no proband', async () => {
  const recorder = recording(200, {
    pedigree_id: PEDIGREE_ID,
    name: 'Empty pedigree',
    proband: null,
    diseases_in_family: {},
  });

  const summary = await clientWith(recorder.fetch).getPedigreeSummary(PEDIGREE_ID);

  strictEqual(summary.probandName, null);
  deepStrictEqual(summary.diseases, []);
});

test('throws EvageneError on non-2xx status', async () => {
  const recorder = recording(404, {});

  await rejects(
    () => clientWith(recorder.fetch).getPedigreeSummary(PEDIGREE_ID),
    EvageneError,
  );
});

test('throws EvageneError when the response shape is unexpected', async () => {
  const recorder = recording(200, { pedigree_id: 42, name: 'oops' });

  await rejects(
    () => clientWith(recorder.fetch).getPedigreeSummary(PEDIGREE_ID),
    EvageneError,
  );
});
