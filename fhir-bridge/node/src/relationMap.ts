/**
 * FHIR <-> Evagene relation code translation.
 *
 * Pure lookup table. The FHIR codes come from the HL7 v3 RoleCode
 * code-system referenced by FHIR R5 FamilyMemberHistory.relationship.
 *
 *   https://hl7.org/fhir/R5/familymemberhistory.html
 *   https://terminology.hl7.org/CodeSystem-v3-RoleCode.html
 *
 * Codes not listed here are reported by `mapToEvagene` as `undefined`;
 * callers surface that as a skip-with-warning, not a hard error.
 */

import type { RelativeType } from './intakeFamily.js';

export const FHIR_V3_ROLE_CODE_SYSTEM = 'http://terminology.hl7.org/CodeSystem/v3-RoleCode';

export type FhirRelationshipCode =
  | 'MTH'
  | 'FTH'
  | 'BRO'
  | 'SIS'
  | 'HBRO'
  | 'HSIS'
  | 'MGRMTH'
  | 'MGRFTH'
  | 'PGRMTH'
  | 'PGRFTH'
  | 'SON'
  | 'DAU'
  | 'MAUNT'
  | 'MUNCLE'
  | 'PAUNT'
  | 'PUNCLE'
  | 'NIECE'
  | 'NEPH'
  | 'COUSN';

interface CodeMapping {
  readonly fhir: FhirRelationshipCode;
  readonly display: string;
  readonly evagene: RelativeType;
}

const MAPPINGS: readonly CodeMapping[] = [
  { fhir: 'MTH', display: 'mother', evagene: 'mother' },
  { fhir: 'FTH', display: 'father', evagene: 'father' },
  { fhir: 'BRO', display: 'brother', evagene: 'brother' },
  { fhir: 'SIS', display: 'sister', evagene: 'sister' },
  { fhir: 'HBRO', display: 'half-brother', evagene: 'half_brother' },
  { fhir: 'HSIS', display: 'half-sister', evagene: 'half_sister' },
  { fhir: 'MGRMTH', display: 'maternal grandmother', evagene: 'maternal_grandmother' },
  { fhir: 'MGRFTH', display: 'maternal grandfather', evagene: 'maternal_grandfather' },
  { fhir: 'PGRMTH', display: 'paternal grandmother', evagene: 'paternal_grandmother' },
  { fhir: 'PGRFTH', display: 'paternal grandfather', evagene: 'paternal_grandfather' },
  { fhir: 'SON', display: 'son', evagene: 'son' },
  { fhir: 'DAU', display: 'daughter', evagene: 'daughter' },
  { fhir: 'MAUNT', display: 'maternal aunt', evagene: 'maternal_aunt' },
  { fhir: 'MUNCLE', display: 'maternal uncle', evagene: 'maternal_uncle' },
  { fhir: 'PAUNT', display: 'paternal aunt', evagene: 'paternal_aunt' },
  { fhir: 'PUNCLE', display: 'paternal uncle', evagene: 'paternal_uncle' },
  { fhir: 'NIECE', display: 'niece', evagene: 'niece' },
  { fhir: 'NEPH', display: 'nephew', evagene: 'nephew' },
  { fhir: 'COUSN', display: 'cousin', evagene: 'first_cousin' },
];

const BY_FHIR = new Map<string, CodeMapping>(MAPPINGS.map(m => [m.fhir, m]));
const BY_EVAGENE = new Map<RelativeType, CodeMapping>(MAPPINGS.map(m => [m.evagene, m]));

export interface FhirCoding {
  readonly code: FhirRelationshipCode;
  readonly display: string;
  readonly system: string;
}

export function mapToFhir(relative: RelativeType): FhirCoding | undefined {
  const mapping = BY_EVAGENE.get(relative);
  if (mapping === undefined) {
    return undefined;
  }
  return { code: mapping.fhir, display: mapping.display, system: FHIR_V3_ROLE_CODE_SYSTEM };
}

export function mapToEvagene(fhirCode: string): RelativeType | undefined {
  return BY_FHIR.get(fhirCode)?.evagene;
}
