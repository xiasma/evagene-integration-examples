/**
 * End-to-end: push a pedigree through a fake FHIR simulator, then pull
 * it back and verify the reconstructed IntakeFamily matches.
 *
 * Uses a single shared HttpGateway fake that routes Evagene URLs to an
 * in-memory Evagene store and FHIR URLs to an in-memory FamilyMember-
 * History store. No network.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { deepStrictEqual, ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { run } from '../src/app.js';
import type { HttpGateway, HttpRequest, HttpResponse } from '../src/httpGateway.js';

const PEDIGREE_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
const FHIR_BASE = 'https://fhir.example/fhir';
const EVAGENE_BASE = 'https://evagene.example';

const FIXTURE_PATH = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  'fixtures',
  'sample-evagene-detail.json',
);
const fixturePedigree = JSON.parse(readFileSync(FIXTURE_PATH, 'utf8')) as Record<string, unknown>;

class MemoryStdout {
  buffer = '';
  write(text: string): void {
    this.buffer += text;
  }
}

interface StoredResource {
  readonly id: string;
  readonly body: Record<string, unknown>;
}

class FhirSimulator {
  private readonly familyHistoryByPatient = new Map<string, StoredResource[]>();
  private nextId = 1;

  handle(request: HttpRequest): HttpResponse {
    if (request.method === 'POST' && request.url === FHIR_BASE) {
      return this.acceptTransaction(request);
    }
    if (request.method === 'GET' && request.url.startsWith(`${FHIR_BASE}/FamilyMemberHistory`)) {
      return this.search(request);
    }
    return jsonResponse(404, { resourceType: 'OperationOutcome' });
  }

  private acceptTransaction(request: HttpRequest): HttpResponse {
    const bundle = request.body as Record<string, unknown>;
    const entries = (bundle.entry as Record<string, unknown>[] | undefined) ?? [];
    const responseEntries: Record<string, unknown>[] = [];
    for (const entry of entries) {
      const resource = entry.resource as Record<string, unknown>;
      const id = `fmh-${(this.nextId++).toString()}`;
      const stored: Record<string, unknown> = { ...resource, id };
      const patientRef = readPatientReference(resource);
      const existing = this.familyHistoryByPatient.get(patientRef) ?? [];
      existing.push({ id, body: stored });
      this.familyHistoryByPatient.set(patientRef, existing);
      responseEntries.push({ response: { status: '201 Created', location: `FamilyMemberHistory/${id}` } });
    }
    return jsonResponse(200, {
      resourceType: 'Bundle',
      type: 'transaction-response',
      entry: responseEntries,
    });
  }

  private search(request: HttpRequest): HttpResponse {
    const patientId = new URL(request.url).searchParams.get('patient') ?? '';
    const patientRef = `Patient/${patientId}`;
    const stored = this.familyHistoryByPatient.get(patientRef) ?? [];
    return jsonResponse(200, {
      resourceType: 'Bundle',
      type: 'searchset',
      entry: stored.map(s => ({ fullUrl: `${FHIR_BASE}/FamilyMemberHistory/${s.id}`, resource: s.body })),
    });
  }
}

class EvageneSimulator {
  public readonly createdIndividuals: Record<string, unknown>[] = [];
  public readonly addRelativeCalls: Record<string, unknown>[] = [];
  public createdPedigreeId: string | undefined;
  public probandId: string | undefined;

  handle(request: HttpRequest): HttpResponse {
    if (request.method === 'GET' && request.url === `${EVAGENE_BASE}/api/pedigrees/${PEDIGREE_ID}`) {
      return jsonResponse(200, fixturePedigree);
    }
    if (request.method === 'POST' && request.url === `${EVAGENE_BASE}/api/pedigrees`) {
      this.createdPedigreeId = 'created-pedigree';
      return jsonResponse(201, { id: this.createdPedigreeId });
    }
    if (request.method === 'POST' && request.url === `${EVAGENE_BASE}/api/individuals`) {
      const body = request.body as Record<string, unknown>;
      const id = `ind-${(this.createdIndividuals.length + 1).toString()}`;
      this.createdIndividuals.push({ id, ...body });
      return jsonResponse(201, { id });
    }
    if (
      request.method === 'POST' &&
      request.url.startsWith(`${EVAGENE_BASE}/api/pedigrees/`) &&
      request.url.endsWith('/register/add-relative')
    ) {
      const body = request.body as Record<string, unknown>;
      const id = `rel-${(this.addRelativeCalls.length + 1).toString()}`;
      this.addRelativeCalls.push({ id, ...body });
      return jsonResponse(201, { individual: { id } });
    }
    if (request.method === 'PATCH' && request.url.startsWith(`${EVAGENE_BASE}/api/individuals/`)) {
      const id = request.url.substring(`${EVAGENE_BASE}/api/individuals/`.length);
      this.probandId = id;
      return jsonResponse(200, { id });
    }
    if (
      request.method === 'POST' &&
      request.url.startsWith(`${EVAGENE_BASE}/api/pedigrees/`) &&
      request.url.includes('/individuals/')
    ) {
      return jsonResponse(204, {});
    }
    return jsonResponse(404, {});
  }
}

class RoutingGateway implements HttpGateway {
  constructor(
    private readonly fhir: FhirSimulator,
    private readonly evagene: EvageneSimulator,
  ) {}
  send(request: HttpRequest): Promise<HttpResponse> {
    if (request.url.startsWith(EVAGENE_BASE)) {
      return Promise.resolve(this.evagene.handle(request));
    }
    if (request.url.startsWith(FHIR_BASE)) {
      return Promise.resolve(this.fhir.handle(request));
    }
    return Promise.resolve(jsonResponse(404, {}));
  }
}

function jsonResponse(status: number, payload: unknown): HttpResponse {
  return {
    status,
    json: () => Promise.resolve(payload),
    text: () => Promise.resolve(JSON.stringify(payload)),
  };
}

function readPatientReference(resource: Record<string, unknown>): string {
  const patient = resource.patient as Record<string, unknown> | undefined;
  return typeof patient?.reference === 'string' ? patient.reference : 'Patient/unknown';
}

test('push then pull reconstructs the family end-to-end', async () => {
  const fhir = new FhirSimulator();
  const evagene = new EvageneSimulator();
  const gateway = new RoutingGateway(fhir, evagene);
  const env = { EVAGENE_API_KEY: 'evg_test', EVAGENE_BASE_URL: EVAGENE_BASE };
  const stdout = new MemoryStdout();
  const stderr = new MemoryStdout();

  const pushExit = await run(
    ['push', PEDIGREE_ID, '--to', FHIR_BASE],
    env,
    { stdout, stderr },
    gateway,
  );

  strictEqual(pushExit, 0, stderr.buffer);
  ok(stdout.buffer.includes('wrote 6 FamilyMemberHistory resources'));
  ok(stdout.buffer.includes('skipped Sam Park'));

  const pullExit = await run(
    ['pull', 'p-proband', '--from', FHIR_BASE],
    env,
    { stdout, stderr },
    gateway,
  );

  strictEqual(pullExit, 0, stderr.buffer);
  strictEqual(evagene.createdPedigreeId, 'created-pedigree');
  strictEqual(evagene.createdIndividuals.length, 1);
  strictEqual(evagene.addRelativeCalls.length, 6);

  const relativeTypes = evagene.addRelativeCalls.map(c => c.relative_type).sort();
  deepStrictEqual(relativeTypes, [
    'brother',
    'father',
    'maternal_grandfather',
    'maternal_grandmother',
    'mother',
    'son',
  ]);
});
