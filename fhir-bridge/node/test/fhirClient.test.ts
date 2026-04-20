import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { FhirApiError, FhirClient } from '../src/fhirClient.js';
import type { FhirBundle } from '../src/fhirTypes.js';
import type { HttpGateway, HttpRequest, HttpResponse } from '../src/httpGateway.js';

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

function clientWith(gateway: HttpGateway, authHeader?: string): FhirClient {
  return new FhirClient(
    authHeader === undefined
      ? { baseUrl: 'https://fhir.example/fhir', http: gateway }
      : { baseUrl: 'https://fhir.example/fhir', http: gateway, authHeader },
  );
}

test('fetch for patient issues GET and returns the Bundle', async () => {
  const bundle: FhirBundle = { resourceType: 'Bundle', type: 'searchset', entry: [] };
  const gateway = new RecordingGateway(stubResponse(200, bundle));

  const result = await clientWith(gateway).fetchFamilyHistoryForPatient('p1');

  strictEqual(gateway.calls.length, 1);
  strictEqual(gateway.calls[0]?.method, 'GET');
  strictEqual(gateway.calls[0]?.url, 'https://fhir.example/fhir/FamilyMemberHistory?patient=p1');
  strictEqual(gateway.calls[0]?.headers.Accept, 'application/fhir+json');
  deepStrictEqual(result, bundle);
});

test('fetch rejects a Bundle that is not searchset/collection', async () => {
  const bad: FhirBundle = { resourceType: 'Bundle', type: 'transaction-response', entry: [] };
  const gateway = new RecordingGateway(stubResponse(200, bad));

  await rejects(() => clientWith(gateway).fetchFamilyHistoryForPatient('p1'), FhirApiError);
});

test('post transaction Bundle sends POST to the base URL', async () => {
  const responseBundle: FhirBundle = {
    resourceType: 'Bundle',
    type: 'transaction-response',
    entry: [{ response: { status: '201 Created', location: 'FamilyMemberHistory/1' } }],
  };
  const gateway = new RecordingGateway(stubResponse(200, responseBundle));
  const txBundle: FhirBundle = { resourceType: 'Bundle', type: 'transaction', entry: [] };

  const result = await clientWith(gateway).postTransactionBundle(txBundle);

  strictEqual(gateway.calls[0]?.method, 'POST');
  strictEqual(gateway.calls[0]?.url, 'https://fhir.example/fhir');
  deepStrictEqual(gateway.calls[0]?.body, txBundle);
  strictEqual(result.entry?.length, 1);
});

test('auth header is forwarded to the FHIR server', async () => {
  const gateway = new RecordingGateway(
    stubResponse(200, { resourceType: 'Bundle', type: 'searchset' }),
  );

  await clientWith(gateway, 'Authorization: Bearer xyz').fetchFamilyHistoryForPatient('p1');

  strictEqual(gateway.calls[0]?.headers.Authorization, 'Bearer xyz');
});

test('non-2xx status raises FhirApiError', async () => {
  const gateway = new RecordingGateway(stubResponse(503, {}));

  await rejects(() => clientWith(gateway).fetchFamilyHistoryForPatient('p1'), FhirApiError);
});
