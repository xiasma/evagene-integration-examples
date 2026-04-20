import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { ApiError, EvageneClient } from '../src/evageneClient.js';
import type { HttpGateway, HttpGatewayOptions, HttpResponse } from '../src/httpGateway.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';
const MINTED_KEY_ID = '22222222-2222-2222-2222-222222222222';

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

function clientWith(gateway: HttpGateway): EvageneClient {
  return new EvageneClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_parent',
    http: gateway,
  });
}

test('createReadOnlyApiKey posts to /api/auth/me/api-keys with read scope only', async () => {
  const gateway = new RecordingGateway(
    stubResponse(201, {
      key: 'evg_minted_plaintext',
      api_key: { id: MINTED_KEY_ID, name: 'share-12345678-x', scopes: ['read'] },
    }),
  );

  const minted = await clientWith(gateway).createReadOnlyApiKey({
    name: 'share-12345678-x',
    ratePerMinute: 60,
    ratePerDay: 1000,
  });

  strictEqual(gateway.lastUrl, 'https://evagene.example/api/auth/me/api-keys');
  strictEqual(gateway.lastHeaders['X-API-Key'], 'evg_parent');
  deepStrictEqual(gateway.lastBody, {
    name: 'share-12345678-x',
    scopes: ['read'],
    rate_limit_per_minute: 60,
    rate_limit_per_day: 1000,
  });
  strictEqual(minted.id, MINTED_KEY_ID);
  strictEqual(minted.plaintextKey, 'evg_minted_plaintext');
});

test('createReadOnlyApiKey throws ApiError on non-2xx', async () => {
  const gateway = new RecordingGateway(stubResponse(403, {}));

  await rejects(
    () =>
      clientWith(gateway).createReadOnlyApiKey({
        name: 'x',
        ratePerMinute: 60,
        ratePerDay: 1000,
      }),
    ApiError,
  );
});

test('createReadOnlyApiKey throws ApiError if plaintext key missing', async () => {
  const gateway = new RecordingGateway(
    stubResponse(201, { api_key: { id: MINTED_KEY_ID } }),
  );

  await rejects(
    () =>
      clientWith(gateway).createReadOnlyApiKey({
        name: 'x',
        ratePerMinute: 60,
        ratePerDay: 1000,
      }),
    ApiError,
  );
});

test('buildEmbedUrl composes pedigree embed path with url-encoded api_key', () => {
  const gateway = new RecordingGateway(stubResponse(200, {}));
  const url = clientWith(gateway).buildEmbedUrl(PEDIGREE_ID, 'evg_with+special/chars');

  strictEqual(
    url,
    `https://evagene.example/api/embed/${PEDIGREE_ID}?api_key=evg_with%2Bspecial%2Fchars`,
  );
});
