import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { EvageneApiError, EvageneClient } from '../src/evageneClient.js';
import type { HttpGateway, HttpGatewayOptions, HttpMethod, HttpResponse } from '../src/httpGateway.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';
const TEMPLATE_ID = '22222222-2222-2222-2222-222222222222';

function stubResponse(status: number, payload: unknown): HttpResponse {
  return {
    status,
    json: () => Promise.resolve(payload),
  };
}

class RecordingGateway implements HttpGateway {
  lastMethod: HttpMethod = 'GET';
  lastUrl = '';
  lastHeaders: Record<string, string> = {};
  lastBody: unknown = undefined;

  constructor(private readonly response: HttpResponse) {}

  send(method: HttpMethod, url: string, options: HttpGatewayOptions): Promise<HttpResponse> {
    this.lastMethod = method;
    this.lastUrl = url;
    this.lastHeaders = options.headers;
    this.lastBody = options.body;
    return Promise.resolve(this.response);
  }
}

function clientWith(gateway: HttpGateway): EvageneClient {
  return new EvageneClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    http: gateway,
  });
}

test('fetchRegister hits the correct URL and parses the payload', async () => {
  const gateway = new RecordingGateway(
    stubResponse(200, {
      proband_id: 'p-1',
      rows: [
        {
          individual_id: 'i-1',
          display_name: 'Sarah',
          relationship_to_proband: 'Sister',
        },
      ],
    }),
  );

  const register = await clientWith(gateway).fetchRegister(PEDIGREE_ID);

  strictEqual(gateway.lastMethod, 'GET');
  strictEqual(
    gateway.lastUrl,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/register`,
  );
  strictEqual(gateway.lastHeaders['X-API-Key'], 'evg_test');
  strictEqual(register.probandId, 'p-1');
  strictEqual(register.rows[0]?.displayName, 'Sarah');
});

test('listTemplates parses an array of templates', async () => {
  const gateway = new RecordingGateway(
    stubResponse(200, [
      { id: 't-1', name: 'foo' },
      { id: 't-2', name: 'bar' },
    ]),
  );

  const templates = await clientWith(gateway).listTemplates();

  deepStrictEqual(
    templates.map(t => t.id),
    ['t-1', 't-2'],
  );
});

test('createTemplate POSTs the body with is_public=false', async () => {
  const gateway = new RecordingGateway(stubResponse(201, { id: 't-new', name: 'cascade' }));

  const created = await clientWith(gateway).createTemplate({
    name: 'cascade',
    description: 'd',
    userPromptTemplate: '{{proband_name}}',
  });

  strictEqual(created.id, 't-new');
  strictEqual(gateway.lastMethod, 'POST');
  strictEqual(gateway.lastUrl, 'https://evagene.example/api/templates');
  const body = gateway.lastBody as Record<string, unknown>;
  strictEqual(body.name, 'cascade');
  strictEqual(body.is_public, false);
});

test('runTemplate puts pedigree_id in the query string', async () => {
  const gateway = new RecordingGateway(stubResponse(200, { text: 'Hello world' }));

  const text = await clientWith(gateway).runTemplate(TEMPLATE_ID, PEDIGREE_ID);

  strictEqual(text, 'Hello world');
  strictEqual(
    gateway.lastUrl,
    `https://evagene.example/api/templates/${TEMPLATE_ID}/run?pedigree_id=${PEDIGREE_ID}`,
  );
});

test('non-2xx status raises EvageneApiError', async () => {
  const gateway = new RecordingGateway(stubResponse(500, {}));

  await rejects(() => clientWith(gateway).fetchRegister(PEDIGREE_ID), EvageneApiError);
});

test('run response missing text field raises EvageneApiError', async () => {
  const gateway = new RecordingGateway(stubResponse(200, { status: 'ok' }));

  await rejects(() => clientWith(gateway).runTemplate(TEMPLATE_ID, PEDIGREE_ID), EvageneApiError);
});
