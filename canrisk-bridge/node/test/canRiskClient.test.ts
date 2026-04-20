import { ok, rejects, strictEqual } from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  ApiError,
  CANRISK_HEADER,
  CanRiskClient,
  CanRiskFormatError,
} from '../src/canRiskClient.js';
import type { HttpGateway, HttpGatewayOptions, HttpResponse } from '../src/httpGateway.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';

const here = dirname(fileURLToPath(import.meta.url));
const fixturesDir = resolve(here, '..', '..', 'fixtures');

function sampleCanRisk(): string {
  return readFileSync(resolve(fixturesDir, 'sample-canrisk.txt'), 'utf8');
}

function stubResponse(status: number, body: string): HttpResponse {
  return {
    status,
    text: () => Promise.resolve(body),
  };
}

class RecordingGateway implements HttpGateway {
  lastUrl = '';
  lastHeaders: Record<string, string> = {};

  constructor(private readonly response: HttpResponse) {}

  getText(url: string, options: HttpGatewayOptions): Promise<HttpResponse> {
    this.lastUrl = url;
    this.lastHeaders = options.headers;
    return Promise.resolve(this.response);
  }
}

function clientWith(gateway: HttpGateway): CanRiskClient {
  return new CanRiskClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    http: gateway,
  });
}

test('GETs the canrisk endpoint with the documented headers', async () => {
  const gateway = new RecordingGateway(stubResponse(200, sampleCanRisk()));

  const body = await clientWith(gateway).fetchForPedigree(PEDIGREE_ID);

  strictEqual(gateway.lastUrl, `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/risk/canrisk`);
  strictEqual(gateway.lastHeaders['X-API-Key'], 'evg_test');
  strictEqual(gateway.lastHeaders.Accept, 'text/tab-separated-values');
  ok(body.startsWith(CANRISK_HEADER));
});

test('throws ApiError on non-2xx status', async () => {
  const gateway = new RecordingGateway(stubResponse(500, ''));

  await rejects(() => clientWith(gateway).fetchForPedigree(PEDIGREE_ID), ApiError);
});

test('throws CanRiskFormatError when header is missing', async () => {
  const gateway = new RecordingGateway(stubResponse(200, 'not a canrisk file'));

  await rejects(() => clientWith(gateway).fetchForPedigree(PEDIGREE_ID), CanRiskFormatError);
});
