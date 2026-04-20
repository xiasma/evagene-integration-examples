import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { MappingError, pedigreeToFhirBundle } from '../src/pedigreeToFhir.js';
import { parsePedigreeDetail } from '../src/pedigreeDetail.js';
import type { FhirFamilyMemberHistory } from '../src/fhirTypes.js';

const FIXTURE_PATH = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  'fixtures',
  'sample-evagene-detail.json',
);
const sample: unknown = JSON.parse(readFileSync(FIXTURE_PATH, 'utf8'));

test('maps the sample pedigree to a transaction Bundle of FamilyMemberHistory', () => {
  const detail = parsePedigreeDetail(sample);

  const { bundle, probandReference, warnings } = pedigreeToFhirBundle(detail);

  strictEqual(bundle.resourceType, 'Bundle');
  strictEqual(bundle.type, 'transaction');
  strictEqual(probandReference, 'Patient/p-proband');
  strictEqual(warnings.length, 1);
  ok(warnings[0]?.includes('Sam Park'));

  const resources: FhirFamilyMemberHistory[] = [];
  for (const entry of bundle.entry ?? []) {
    if (entry.resource !== undefined) {
      resources.push(entry.resource);
    }
  }
  const names = resources.map(r => r.name);
  ok(names.includes('Linda Chen'));
  ok(names.includes('David Chen'));
  ok(names.includes('Mary Chen'));
  ok(names.includes('Robert Chen'));
  ok(names.includes('James Chen'));
  ok(names.includes('Noah Chen'));

  const findBy = (name: string) => resources.find(r => r.name === name);
  strictEqual(findBy('Linda Chen')?.relationship.coding?.[0]?.code, 'MTH');
  strictEqual(findBy('Mary Chen')?.relationship.coding?.[0]?.code, 'MGRMTH');
  strictEqual(findBy('James Chen')?.relationship.coding?.[0]?.code, 'BRO');
  strictEqual(findBy('Noah Chen')?.relationship.coding?.[0]?.code, 'SON');
  strictEqual(findBy('Linda Chen')?.bornDate, '1962-09-14');
});

test('every supported relative_type produces a recognisable FHIR code', () => {
  const detail = parsePedigreeDetail({
    id: 'ped-1',
    display_name: 'empty',
    individuals: [
      { id: 'p', display_name: 'P', biological_sex: 'female', proband: 1, events: [] },
    ],
    relationships: [],
    eggs: [],
  });

  const result = pedigreeToFhirBundle(detail);

  strictEqual(result.bundle.entry?.length, 0);
  strictEqual(result.warnings.length, 0);
});

test('a pedigree without a proband is rejected', () => {
  const detail = parsePedigreeDetail({
    id: 'ped-1',
    display_name: 'no proband',
    individuals: [
      { id: 'p', display_name: 'P', biological_sex: 'female', proband: 0, events: [] },
    ],
    relationships: [],
    eggs: [],
  });

  try {
    pedigreeToFhirBundle(detail);
    ok(false, 'expected MappingError');
  } catch (error) {
    ok(error instanceof MappingError);
  }
});
