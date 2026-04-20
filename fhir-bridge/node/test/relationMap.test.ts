import { strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { RelativeType } from '../src/intakeFamily.js';
import { FHIR_V3_ROLE_CODE_SYSTEM, mapToEvagene, mapToFhir } from '../src/relationMap.js';

const ROUND_TRIPS: readonly (readonly [RelativeType, string])[] = [
  ['mother', 'MTH'],
  ['father', 'FTH'],
  ['brother', 'BRO'],
  ['sister', 'SIS'],
  ['half_brother', 'HBRO'],
  ['half_sister', 'HSIS'],
  ['maternal_grandmother', 'MGRMTH'],
  ['maternal_grandfather', 'MGRFTH'],
  ['paternal_grandmother', 'PGRMTH'],
  ['paternal_grandfather', 'PGRFTH'],
  ['son', 'SON'],
  ['daughter', 'DAU'],
  ['maternal_aunt', 'MAUNT'],
  ['maternal_uncle', 'MUNCLE'],
  ['paternal_aunt', 'PAUNT'],
  ['paternal_uncle', 'PUNCLE'],
  ['niece', 'NIECE'],
  ['nephew', 'NEPH'],
  ['first_cousin', 'COUSN'],
];

for (const [evagene, fhir] of ROUND_TRIPS) {
  test(`${evagene} <-> ${fhir} round-trips both ways`, () => {
    const coding = mapToFhir(evagene);
    if (coding === undefined) {
      throw new Error(`mapToFhir returned undefined for ${evagene}`);
    }
    strictEqual(coding.code, fhir);
    strictEqual(coding.system, FHIR_V3_ROLE_CODE_SYSTEM);
    strictEqual(mapToEvagene(fhir), evagene);
  });
}

test('unknown FHIR code returns undefined, not a fabricated relation', () => {
  strictEqual(mapToEvagene('SPOUSE'), undefined);
  strictEqual(mapToEvagene(''), undefined);
});
