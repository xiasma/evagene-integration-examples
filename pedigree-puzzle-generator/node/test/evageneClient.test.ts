import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import {
  type AddRelativeArgs,
  DiseaseNotFoundError,
  EvageneApiError,
  EvageneClient,
} from '../src/evageneClient.js';
import type { HttpGateway, HttpGatewayOptions, HttpResponse } from '../src/httpGateway.js';

const PEDIGREE_ID = '11111111-1111-1111-1111-111111111111';
const INDIVIDUAL_ID = '22222222-2222-2222-2222-222222222222';
const DISEASE_ID = '33333333-3333-3333-3333-333333333333';

class ScriptedGateway implements HttpGateway {
  calls: HttpGatewayOptions[] = [];
  constructor(private readonly script: Map<string, HttpResponse>) {}
  send(options: HttpGatewayOptions): Promise<HttpResponse> {
    this.calls.push(options);
    for (const [key, response] of this.script) {
      const [wantMethod, wantSuffix] = key.split(' ');
      if (options.method === wantMethod && options.url.endsWith(wantSuffix ?? '')) {
        return Promise.resolve(response);
      }
    }
    return Promise.reject(new Error(`unscripted: ${options.method} ${options.url}`));
  }
}

function stubResponse(status: number, payload?: unknown, text = ''): HttpResponse {
  return {
    status,
    text: () => Promise.resolve(text),
    json: () =>
      payload === undefined
        ? Promise.reject(new SyntaxError('no JSON body'))
        : Promise.resolve(payload),
  };
}

function clientWith(gateway: ScriptedGateway): EvageneClient {
  return new EvageneClient({
    baseUrl: 'https://evagene.example',
    apiKey: 'evg_test',
    http: gateway,
  });
}

function onlyCall(gateway: ScriptedGateway): HttpGatewayOptions {
  const [call] = gateway.calls;
  if (call === undefined) throw new Error('expected one recorded call');
  return call;
}

test('searchDiseases returns matching entry', async () => {
  const gateway = new ScriptedGateway(
    new Map([
      [
        'GET /api/diseases',
        stubResponse(200, [
          { id: 'aaa', display_name: 'Some other disease' },
          { id: DISEASE_ID, display_name: 'Cystic Fibrosis' },
        ]),
      ],
    ]),
  );

  const summary = await clientWith(gateway).searchDiseases('cystic');

  strictEqual(summary.diseaseId, DISEASE_ID);
  strictEqual(summary.displayName, 'Cystic Fibrosis');
});

test('searchDiseases prefers exact match over substring', async () => {
  const gateway = new ScriptedGateway(
    new Map([
      [
        'GET /api/diseases',
        stubResponse(200, [
          { id: 'pulmonary', display_name: 'Cystic Fibrosis (Pulmonary)' },
          { id: DISEASE_ID, display_name: 'Cystic Fibrosis' },
        ]),
      ],
    ]),
  );

  const summary = await clientWith(gateway).searchDiseases('Cystic Fibrosis');

  strictEqual(summary.diseaseId, DISEASE_ID);
});

test('searchDiseases raises when no match', async () => {
  const gateway = new ScriptedGateway(
    new Map([['GET /api/diseases', stubResponse(200, [])]]),
  );
  await rejects(() => clientWith(gateway).searchDiseases('unobtainable'), DiseaseNotFoundError);
});

test('createPedigree posts display name and returns id', async () => {
  const gateway = new ScriptedGateway(
    new Map([['POST /api/pedigrees', stubResponse(201, { id: PEDIGREE_ID })]]),
  );

  const returned = await clientWith(gateway).createPedigree('Puzzle pedigree');

  strictEqual(returned, PEDIGREE_ID);
  const call = onlyCall(gateway);
  strictEqual(call.method, 'POST');
  strictEqual(call.url, 'https://evagene.example/api/pedigrees');
  deepStrictEqual(call.body, { display_name: 'Puzzle pedigree' });
});

test('createIndividual sends sex and returns id', async () => {
  const gateway = new ScriptedGateway(
    new Map([['POST /api/individuals', stubResponse(201, { id: INDIVIDUAL_ID })]]),
  );

  const returned = await clientWith(gateway).createIndividual({
    displayName: 'Person 1',
    sex: 'female',
  });

  strictEqual(returned, INDIVIDUAL_ID);
  deepStrictEqual(onlyCall(gateway).body, {
    display_name: 'Person 1',
    biological_sex: 'female',
  });
});

test('addIndividualToPedigree tolerates empty body', async () => {
  const gateway = new ScriptedGateway(
    new Map([
      [
        `POST /api/pedigrees/${PEDIGREE_ID}/individuals/${INDIVIDUAL_ID}`,
        stubResponse(204),
      ],
    ]),
  );

  await clientWith(gateway).addIndividualToPedigree(PEDIGREE_ID, INDIVIDUAL_ID);

  const call = onlyCall(gateway);
  strictEqual(call.method, 'POST');
  deepStrictEqual(call.body, {});
});

test('designateAsProband patches proband=1', async () => {
  const gateway = new ScriptedGateway(
    new Map([[`PATCH /api/individuals/${INDIVIDUAL_ID}`, stubResponse(204)]]),
  );

  await clientWith(gateway).designateAsProband(INDIVIDUAL_ID);

  const call = onlyCall(gateway);
  strictEqual(call.method, 'PATCH');
  deepStrictEqual(call.body, { proband: 1 });
});

test('addRelative returns new individual id', async () => {
  const gateway = new ScriptedGateway(
    new Map([
      [
        `POST /api/pedigrees/${PEDIGREE_ID}/register/add-relative`,
        stubResponse(201, { individual: { id: INDIVIDUAL_ID } }),
      ],
    ]),
  );

  const args: AddRelativeArgs = {
    pedigreeId: PEDIGREE_ID,
    relativeOf: 'anchor-id',
    relativeType: 'mother',
    displayName: 'Person 2',
    sex: 'female',
  };
  const returned = await clientWith(gateway).addRelative(args);

  strictEqual(returned, INDIVIDUAL_ID);
  deepStrictEqual(onlyCall(gateway).body, {
    relative_of: 'anchor-id',
    relative_type: 'mother',
    display_name: 'Person 2',
    biological_sex: 'female',
  });
});

test('addDiseaseToIndividual posts disease id', async () => {
  const gateway = new ScriptedGateway(
    new Map([
      [
        `POST /api/individuals/${INDIVIDUAL_ID}/diseases`,
        stubResponse(201, { disease_id: DISEASE_ID }),
      ],
    ]),
  );

  await clientWith(gateway).addDiseaseToIndividual(INDIVIDUAL_ID, DISEASE_ID);

  deepStrictEqual(onlyCall(gateway).body, { disease_id: DISEASE_ID });
});

test('getPedigreeSvg returns response text', async () => {
  const gateway = new ScriptedGateway(
    new Map([
      [
        `GET /api/pedigrees/${PEDIGREE_ID}/export.svg`,
        stubResponse(200, undefined, '<svg></svg>'),
      ],
    ]),
  );

  const svg = await clientWith(gateway).getPedigreeSvg(PEDIGREE_ID);

  strictEqual(svg, '<svg></svg>');
});

test('deletePedigree sends DELETE', async () => {
  const gateway = new ScriptedGateway(
    new Map([[`DELETE /api/pedigrees/${PEDIGREE_ID}`, stubResponse(204)]]),
  );

  await clientWith(gateway).deletePedigree(PEDIGREE_ID);

  const call = onlyCall(gateway);
  strictEqual(call.method, 'DELETE');
  strictEqual(call.url, `https://evagene.example/api/pedigrees/${PEDIGREE_ID}`);
});

test('non-2xx raises EvageneApiError', async () => {
  const gateway = new ScriptedGateway(
    new Map([['POST /api/pedigrees', stubResponse(500, {})]]),
  );
  await rejects(() => clientWith(gateway).createPedigree('x'), EvageneApiError);
});

test('missing id raises EvageneApiError', async () => {
  const gateway = new ScriptedGateway(
    new Map([['POST /api/pedigrees', stubResponse(201, { not_id: 'x' })]]),
  );
  await rejects(() => clientWith(gateway).createPedigree('x'), EvageneApiError);
});
