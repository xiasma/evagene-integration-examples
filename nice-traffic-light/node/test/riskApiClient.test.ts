import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { HttpGateway, HttpGatewayOptions, HttpResponse } from '../src/httpGateway.js';
import { ApiError, RiskApiClient } from '../src/riskApiClient.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';
const COUNSELEE_ID = '22222222-2222-2222-2222-222222222222';

function stubResponse(status: number, payload: unknown): HttpResponse {
  return {
    status,
    json: () => Promise.resolve(payload),
  };
}

class RecordingGateway implements HttpGateway {
  lastUrl = '';
  lastHeaders: Record<string, string> = {};
  lastBody: unknown = undefined;

  constructor(private readonly response: HttpResponse) {}

  postJson(url: string, options: HttpGatewayOptions): Promise<HttpResponse> {
    this.lastUrl = url;
    this.lastHeaders = options.headers;
    this.lastBody = options.body;
    return Promise.resolve(this.response);
  }
}

function clientWith(gateway: HttpGateway): RiskApiClient {
  return new RiskApiClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    http: gateway,
  });
}

test('posts NICE model to risk/calculate', async () => {
  const gateway = new RecordingGateway(
    stubResponse(200, { cancer_risk: { nice_category: 'near_population' } }),
  );

  await clientWith(gateway).calculateNice({ pedigreeId: PEDIGREE_ID });

  strictEqual(
    gateway.lastUrl,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/risk/calculate`,
  );
  strictEqual(gateway.lastHeaders['X-API-Key'], 'evg_test');
  deepStrictEqual(gateway.lastBody, { model: 'NICE' });
});

test('includes counselee_id when provided', async () => {
  const gateway = new RecordingGateway(stubResponse(200, {}));

  await clientWith(gateway).calculateNice({
    pedigreeId: PEDIGREE_ID,
    counseleeId: COUNSELEE_ID,
  });

  deepStrictEqual(gateway.lastBody, { model: 'NICE', counselee_id: COUNSELEE_ID });
});

test('throws ApiError on non-2xx status', async () => {
  const gateway = new RecordingGateway(stubResponse(500, {}));

  await rejects(
    () => clientWith(gateway).calculateNice({ pedigreeId: PEDIGREE_ID }),
    ApiError,
  );
});
