import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { EvageneApiError, EvageneClient } from '../src/evageneClient.js';
import type { HttpGateway, HttpRequest, HttpResponse } from '../src/httpGateway.js';

const BASE = 'https://evagene.example';
const PEDIGREE_ID = 'a1cfe665-0000-4000-8000-000000000001';

class RecordingGateway implements HttpGateway {
  readonly requests: HttpRequest[] = [];
  private responses: HttpResponse[];

  constructor(...responses: HttpResponse[]) {
    this.responses = [...responses];
  }

  send(request: HttpRequest): Promise<HttpResponse> {
    this.requests.push(request);
    const next = this.responses.shift();
    if (next === undefined) {
      throw new Error(`Gateway exhausted on ${request.method} ${request.url}`);
    }
    return Promise.resolve(next);
  }
}

function stub(status: number, payload: unknown): HttpResponse {
  return { status, json: () => Promise.resolve(payload) };
}

function clientWith(gateway: HttpGateway): EvageneClient {
  return new EvageneClient({ baseUrl: BASE, apiKey: 'evg_test', http: gateway });
}

test('getPedigreeSummary returns display name and proband name', async () => {
  const gateway = new RecordingGateway(
    stub(200, { name: 'Windsor BRCA branch', proband: { name: 'Elizabeth', sex: 'female' } }),
  );

  const summary = await clientWith(gateway).getPedigreeSummary(PEDIGREE_ID);

  strictEqual(summary.displayName, 'Windsor BRCA branch');
  strictEqual(summary.probandName, 'Elizabeth');
  strictEqual(gateway.requests[0]?.method, 'GET');
  strictEqual(gateway.requests[0]?.url, `${BASE}/api/pedigrees/${PEDIGREE_ID}/summary`);
  strictEqual(gateway.requests[0]?.headers['X-API-Key'], 'evg_test');
});

test('getPedigreeSummary leaves probandName undefined when no proband designated', async () => {
  const gateway = new RecordingGateway(stub(200, { name: 'Orphan', proband: null }));

  const summary = await clientWith(gateway).getPedigreeSummary(PEDIGREE_ID);

  strictEqual(summary.probandName, undefined);
});

test('svgUrlFor and pedigreeWebUrlFor produce canonical URLs', () => {
  const client = clientWith(new RecordingGateway());
  strictEqual(client.svgUrlFor(PEDIGREE_ID), `${BASE}/api/pedigrees/${PEDIGREE_ID}/export.svg`);
  strictEqual(client.pedigreeWebUrlFor(PEDIGREE_ID), `${BASE}/pedigrees/${PEDIGREE_ID}`);
});

test('calculateNice posts model=NICE and returns GREEN/AMBER/RED', async () => {
  const gateway = new RecordingGateway(
    stub(200, {
      cancer_risk: {
        nice_category: 'high',
        nice_refer_genetics: true,
        nice_triggers: ['Mother affected <40', 'Two first-degree relatives'],
      },
    }),
  );

  const result = await clientWith(gateway).calculateNice(PEDIGREE_ID);

  strictEqual(result.category, 'RED');
  strictEqual(result.referForGeneticsAssessment, true);
  deepStrictEqual(result.triggers, ['Mother affected <40', 'Two first-degree relatives']);
  deepStrictEqual(gateway.requests[0]?.body, { model: 'NICE' });
});

test('calculateNice maps near_population to GREEN', async () => {
  const gateway = new RecordingGateway(
    stub(200, {
      cancer_risk: { nice_category: 'near_population', nice_refer_genetics: false, nice_triggers: [] },
    }),
  );
  const result = await clientWith(gateway).calculateNice(PEDIGREE_ID);
  strictEqual(result.category, 'GREEN');
});

test('calculateNice rejects unknown NICE category with a schema error', async () => {
  const gateway = new RecordingGateway(
    stub(200, { cancer_risk: { nice_category: 'unknown', nice_refer_genetics: false } }),
  );
  await rejects(() => clientWith(gateway).calculateNice(PEDIGREE_ID), EvageneApiError);
});

test('non-2xx response surfaces an EvageneApiError', async () => {
  const gateway = new RecordingGateway(stub(503, {}));
  await rejects(() => clientWith(gateway).getPedigreeSummary(PEDIGREE_ID), EvageneApiError);
});
