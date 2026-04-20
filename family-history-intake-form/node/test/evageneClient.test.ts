import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { EvageneApiError, EvageneClient } from '../src/evageneClient.js';
import type {
  HttpGateway,
  HttpGatewayOptions,
  HttpResponse,
} from '../src/httpGateway.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';
const INDIVIDUAL_ID = '22222222-2222-2222-2222-222222222222';

class RecordingGateway implements HttpGateway {
  calls: HttpGatewayOptions[] = [];

  constructor(private readonly response: HttpResponse) {}

  send(options: HttpGatewayOptions): Promise<HttpResponse> {
    this.calls.push(options);
    return Promise.resolve(this.response);
  }
}

function stubResponse(status: number, payload: unknown): HttpResponse {
  return {
    status,
    json: () => Promise.resolve(payload),
  };
}

function emptyBodyResponse(status: number): HttpResponse {
  return {
    status,
    json: () => Promise.reject(new SyntaxError('no JSON body')),
  };
}

function clientWith(gateway: HttpGateway): EvageneClient {
  return new EvageneClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    http: gateway,
  });
}

function onlyCall(gateway: RecordingGateway): HttpGatewayOptions {
  const [call] = gateway.calls;
  if (call === undefined) {
    throw new Error('expected at least one recorded HTTP call');
  }
  return call;
}

test('createPedigree POSTs display name and returns id', async () => {
  const gateway = new RecordingGateway(stubResponse(201, { id: PEDIGREE_ID }));

  const id = await clientWith(gateway).createPedigree({ displayName: 'Emma\u2019s family' });

  strictEqual(id, PEDIGREE_ID);
  strictEqual(gateway.calls.length, 1);
  const call = onlyCall(gateway);
  strictEqual(call.method, 'POST');
  strictEqual(call.url, 'https://evagene.example/api/pedigrees');
  strictEqual(call.headers['X-API-Key'], 'evg_test');
  deepStrictEqual(call.body, { display_name: 'Emma\u2019s family' });
});

test('createIndividual includes biological sex and optional year', async () => {
  const gateway = new RecordingGateway(stubResponse(201, { id: INDIVIDUAL_ID }));

  await clientWith(gateway).createIndividual({
    displayName: 'Emma',
    biologicalSex: 'female',
    yearOfBirth: 1985,
  });

  deepStrictEqual(onlyCall(gateway).body, {
    display_name: 'Emma',
    biological_sex: 'female',
    properties: { year_of_birth: 1985 },
  });
});

test('designateAsProband PATCHes proband=1 on the individual', async () => {
  const gateway = new RecordingGateway(stubResponse(200, { id: INDIVIDUAL_ID }));

  await clientWith(gateway).designateAsProband(INDIVIDUAL_ID);

  const call = onlyCall(gateway);
  strictEqual(call.method, 'PATCH');
  strictEqual(call.url, `https://evagene.example/api/individuals/${INDIVIDUAL_ID}`);
  deepStrictEqual(call.body, { proband: 1 });
});

test('addRelative returns the new individual id', async () => {
  const gateway = new RecordingGateway(
    stubResponse(201, { individual: { id: INDIVIDUAL_ID } }),
  );

  const id = await clientWith(gateway).addRelative({
    pedigreeId: PEDIGREE_ID,
    relativeOf: 'proband-id',
    relativeType: 'mother',
    displayName: 'Grace',
    biologicalSex: 'female',
  });

  strictEqual(id, INDIVIDUAL_ID);
  const call = onlyCall(gateway);
  strictEqual(
    call.url,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/register/add-relative`,
  );
  deepStrictEqual(call.body, {
    relative_of: 'proband-id',
    relative_type: 'mother',
    display_name: 'Grace',
    biological_sex: 'female',
  });
});

test('addIndividualToPedigree tolerates an empty response body', async () => {
  const gateway = new RecordingGateway(emptyBodyResponse(204));

  await clientWith(gateway).addIndividualToPedigree(PEDIGREE_ID, INDIVIDUAL_ID);

  const call = onlyCall(gateway);
  strictEqual(call.method, 'POST');
  strictEqual(
    call.url,
    `https://evagene.example/api/pedigrees/${PEDIGREE_ID}/individuals/${INDIVIDUAL_ID}`,
  );
  deepStrictEqual(call.body, {});
});

test('designateAsProband tolerates an empty response body', async () => {
  const gateway = new RecordingGateway(emptyBodyResponse(204));

  await clientWith(gateway).designateAsProband(INDIVIDUAL_ID);

  const call = onlyCall(gateway);
  strictEqual(call.method, 'PATCH');
  strictEqual(call.url, `https://evagene.example/api/individuals/${INDIVIDUAL_ID}`);
  deepStrictEqual(call.body, { proband: 1 });
});

test('non-2xx response raises EvageneApiError', async () => {
  const gateway = new RecordingGateway(stubResponse(500, {}));

  await rejects(
    () => clientWith(gateway).createPedigree({ displayName: 'Emma' }),
    EvageneApiError,
  );
});

test('response missing id raises EvageneApiError', async () => {
  const gateway = new RecordingGateway(stubResponse(201, { not_id: 'x' }));

  await rejects(
    () => clientWith(gateway).createPedigree({ displayName: 'Emma' }),
    EvageneApiError,
  );
});
