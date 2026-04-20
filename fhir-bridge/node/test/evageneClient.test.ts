import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { EvageneApiError, EvageneClient } from '../src/evageneClient.js';
import type { HttpGateway, HttpRequest, HttpResponse } from '../src/httpGateway.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';
const INDIVIDUAL_ID = '22222222-2222-2222-2222-222222222222';

class RecordingGateway implements HttpGateway {
  calls: HttpRequest[] = [];
  constructor(private readonly response: HttpResponse) {}
  send(request: HttpRequest): Promise<HttpResponse> {
    this.calls.push(request);
    return Promise.resolve(this.response);
  }
}

function stubResponse(status: number, payload: unknown): HttpResponse {
  return {
    status,
    json: () => Promise.resolve(payload),
    text: () => Promise.resolve(JSON.stringify(payload)),
  };
}

function emptyBodyResponse(status: number): HttpResponse {
  return {
    status,
    json: () => Promise.reject(new SyntaxError('no JSON body')),
    text: () => Promise.resolve(''),
  };
}

function clientWith(gateway: HttpGateway): EvageneClient {
  return new EvageneClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    http: gateway,
  });
}

test('getPedigreeDetail issues GET with API key header', async () => {
  const gateway = new RecordingGateway(stubResponse(200, { id: PEDIGREE_ID }));

  const result = await clientWith(gateway).getPedigreeDetail(PEDIGREE_ID);

  strictEqual(gateway.calls[0]?.method, 'GET');
  strictEqual(gateway.calls[0]?.url, `https://evagene.example/api/pedigrees/${PEDIGREE_ID}`);
  strictEqual(gateway.calls[0]?.headers['X-API-Key'], 'evg_test');
  deepStrictEqual(result, { id: PEDIGREE_ID });
});

test('createPedigree POSTs display name and returns id', async () => {
  const gateway = new RecordingGateway(stubResponse(201, { id: PEDIGREE_ID }));

  const id = await clientWith(gateway).createPedigree({ displayName: 'Emma' });

  strictEqual(id, PEDIGREE_ID);
  strictEqual(gateway.calls[0]?.method, 'POST');
  deepStrictEqual(gateway.calls[0]?.body, { display_name: 'Emma' });
});

test('addRelative returns the new individual id', async () => {
  const gateway = new RecordingGateway(stubResponse(201, { individual: { id: INDIVIDUAL_ID } }));

  const id = await clientWith(gateway).addRelative({
    pedigreeId: PEDIGREE_ID,
    relativeOf: 'proband',
    relativeType: 'mother',
    displayName: 'Grace',
    biologicalSex: 'female',
  });

  strictEqual(id, INDIVIDUAL_ID);
});

test('addIndividualToPedigree tolerates an empty body', async () => {
  const gateway = new RecordingGateway(emptyBodyResponse(204));

  await clientWith(gateway).addIndividualToPedigree(PEDIGREE_ID, INDIVIDUAL_ID);

  strictEqual(gateway.calls[0]?.method, 'POST');
  strictEqual(
    gateway.calls[0]?.url,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/individuals/${INDIVIDUAL_ID}`,
  );
});

test('deletePedigree issues DELETE', async () => {
  const gateway = new RecordingGateway(emptyBodyResponse(204));

  await clientWith(gateway).deletePedigree(PEDIGREE_ID);

  strictEqual(gateway.calls[0]?.method, 'DELETE');
  strictEqual(gateway.calls[0]?.url, `https://evagene.example/api/pedigrees/${PEDIGREE_ID}`);
});

test('non-2xx response raises EvageneApiError', async () => {
  const gateway = new RecordingGateway(stubResponse(500, {}));

  await rejects(
    () => clientWith(gateway).createPedigree({ displayName: 'Emma' }),
    EvageneApiError,
  );
});
