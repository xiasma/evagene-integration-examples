import { rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { EvageneApiError, EvageneClient } from '../src/evageneClient.js';
import type { HttpGateway, JsonResponse, TextResponse } from '../src/httpGateway.js';

interface RecordedCall {
  readonly method: 'GET' | 'POST';
  readonly url: string;
  readonly headers: Readonly<Record<string, string>>;
  readonly body?: unknown;
}

class FakeGateway implements HttpGateway {
  readonly calls: RecordedCall[] = [];

  constructor(
    private readonly textResponses: Record<string, TextResponse>,
    private readonly jsonResponses: Record<string, JsonResponse>,
  ) {}

  getText(url: string, headers: Readonly<Record<string, string>>): Promise<TextResponse> {
    this.calls.push({ method: 'GET', url, headers });
    const response = this.textResponses[url];
    if (!response) throw new Error(`Unexpected GET ${url}`);
    return Promise.resolve(response);
  }

  postJson(
    url: string,
    headers: Readonly<Record<string, string>>,
    body: unknown,
  ): Promise<JsonResponse> {
    this.calls.push({ method: 'POST', url, headers, body });
    const response = this.jsonResponses[url];
    if (!response) throw new Error(`Unexpected POST ${url}`);
    return Promise.resolve(response);
  }
}

function textResponse(status: number, text: string): TextResponse {
  return { status, text: () => Promise.resolve(text) };
}

function jsonResponse(status: number, payload: unknown): JsonResponse {
  return { status, json: () => Promise.resolve(payload) };
}

const BASE_URL = 'https://evagene.example';
const API_KEY = 'evg_test';
const PEDIGREE_ID = 'a1cfe665-3b2d-4f5e-9c1a-8d7e6f5a4b3c';

test('fetchEmbedSvg calls GET /api/embed/:id/svg with the API key and returns the SVG body', async () => {
  const gateway = new FakeGateway(
    {
      [`${BASE_URL}/api/embed/${PEDIGREE_ID}/svg`]: textResponse(200, '<svg>ok</svg>'),
    },
    {},
  );
  const client = new EvageneClient({ baseUrl: BASE_URL, apiKey: API_KEY, http: gateway });

  const svg = await client.fetchEmbedSvg(PEDIGREE_ID);

  strictEqual(svg, '<svg>ok</svg>');
  strictEqual(gateway.calls[0]?.method, 'GET');
  strictEqual(gateway.calls[0]?.headers['X-API-Key'], API_KEY);
});

test('calculateNice POSTs {model: "NICE"} to /risk/calculate and returns the payload', async () => {
  const payload = { cancer_risk: { nice_category: 'moderate' } };
  const gateway = new FakeGateway(
    {},
    {
      [`${BASE_URL}/api/pedigrees/${PEDIGREE_ID}/risk/calculate`]: jsonResponse(200, payload),
    },
  );
  const client = new EvageneClient({ baseUrl: BASE_URL, apiKey: API_KEY, http: gateway });

  const result = await client.calculateNice(PEDIGREE_ID);

  strictEqual(result, payload);
  const call = gateway.calls[0];
  strictEqual(call?.method, 'POST');
  strictEqual(call.headers['Content-Type'], 'application/json');
  strictEqual((call.body as { model: string }).model, 'NICE');
});

test('getPedigreeSummary returns id and display_name from the detail endpoint', async () => {
  const gateway = new FakeGateway(
    {
      [`${BASE_URL}/api/pedigrees/${PEDIGREE_ID}`]: textResponse(
        200,
        JSON.stringify({ id: PEDIGREE_ID, display_name: 'Test family' }),
      ),
    },
    {},
  );
  const client = new EvageneClient({ baseUrl: BASE_URL, apiKey: API_KEY, http: gateway });

  const summary = await client.getPedigreeSummary(PEDIGREE_ID);

  strictEqual(summary.id, PEDIGREE_ID);
  strictEqual(summary.displayName, 'Test family');
});

test('a non-2xx response raises EvageneApiError', async () => {
  const gateway = new FakeGateway(
    {
      [`${BASE_URL}/api/embed/${PEDIGREE_ID}/svg`]: textResponse(404, 'missing'),
    },
    {},
  );
  const client = new EvageneClient({ baseUrl: BASE_URL, apiKey: API_KEY, http: gateway });

  await rejects(() => client.fetchEmbedSvg(PEDIGREE_ID), EvageneApiError);
});

test('getPedigreeSummary raises EvageneApiError when display_name is missing', async () => {
  const gateway = new FakeGateway(
    {
      [`${BASE_URL}/api/pedigrees/${PEDIGREE_ID}`]: textResponse(
        200,
        JSON.stringify({ id: PEDIGREE_ID }),
      ),
    },
    {},
  );
  const client = new EvageneClient({ baseUrl: BASE_URL, apiKey: API_KEY, http: gateway });

  await rejects(() => client.getPedigreeSummary(PEDIGREE_ID), EvageneApiError);
});
