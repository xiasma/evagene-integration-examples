import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { deepStrictEqual, ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { fhirBundleToIntakeFamily } from '../src/fhirToIntake.js';

const FIXTURE_PATH = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  'fixtures',
  'sample-fhir-bundle.json',
);
const sample: unknown = JSON.parse(readFileSync(FIXTURE_PATH, 'utf8'));

test('maps FHIR bundle to IntakeFamily with one relative per known code', () => {
  const { family, warnings } = fhirBundleToIntakeFamily(sample, {
    patientId: 'patient-emma',
    probandDisplayName: 'Emma Chen',
  });

  strictEqual(warnings.length, 0);
  strictEqual(family.proband.displayName, 'Emma Chen');
  strictEqual(family.relatives.length, 6);
  const byType = new Map(family.relatives.map(r => [r.relativeType, r]));
  strictEqual(byType.get('mother')?.displayName, 'Linda Chen');
  strictEqual(byType.get('father')?.displayName, 'David Chen');
  strictEqual(byType.get('maternal_grandmother')?.displayName, 'Mary Chen');
  strictEqual(byType.get('maternal_grandfather')?.displayName, 'Robert Chen');
  strictEqual(byType.get('brother')?.displayName, 'James Chen');
  strictEqual(byType.get('son')?.displayName, 'Noah Chen');
  strictEqual(byType.get('mother')?.yearOfBirth, 1962);
  strictEqual(byType.get('mother')?.biologicalSex, 'female');
});

test('unknown relationship code is reported but does not abort the mapping', () => {
  const bundle = {
    resourceType: 'Bundle',
    type: 'searchset',
    entry: [
      {
        resource: {
          resourceType: 'FamilyMemberHistory',
          id: 'fmh-stepmum',
          status: 'completed',
          patient: { reference: 'Patient/p1' },
          name: 'Sarah',
          relationship: {
            coding: [
              {
                system: 'http://terminology.hl7.org/CodeSystem/v3-RoleCode',
                code: 'STPMTH',
              },
            ],
          },
        },
      },
    ],
  };

  const { family, warnings } = fhirBundleToIntakeFamily(bundle, { patientId: 'p1' });

  strictEqual(family.relatives.length, 0);
  strictEqual(warnings.length, 1);
  ok(warnings[0]?.includes('STPMTH'));
});

test('non-Bundle input is rejected', () => {
  try {
    fhirBundleToIntakeFamily({ resourceType: 'Patient' }, { patientId: 'p1' });
    ok(false, 'expected MappingError');
  } catch (error) {
    ok(error instanceof Error);
  }
});

test('a FamilyMemberHistory without v3 coding is skipped with a warning', () => {
  const bundle = {
    resourceType: 'Bundle',
    type: 'searchset',
    entry: [
      {
        resource: {
          resourceType: 'FamilyMemberHistory',
          id: 'fmh-bare',
          status: 'completed',
          patient: { reference: 'Patient/p1' },
          relationship: { text: 'mother-ish' },
        },
      },
    ],
  };
  const { family, warnings } = fhirBundleToIntakeFamily(bundle, { patientId: 'p1' });
  deepStrictEqual(family.relatives, []);
  strictEqual(warnings.length, 1);
});
