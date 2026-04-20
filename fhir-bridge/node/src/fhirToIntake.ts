/**
 * FHIR R5 Bundle -> IntakeFamily.
 *
 * Reads FamilyMemberHistory resources, maps their relationship code to
 * an Evagene relative_type, and emits a flat proband+relatives shape
 * the IntakeService can create in Evagene.
 *
 * Pure transformation: unknown codes produce warnings, never exceptions.
 */

import type {
  FhirBundle,
  FhirBundleEntry,
  FhirCodeableConcept,
  FhirFamilyMemberHistory,
} from './fhirTypes.js';
import type {
  BiologicalSex,
  IntakeFamily,
  Relative,
  RelativeType,
} from './intakeFamily.js';
import { MappingError } from './pedigreeToFhir.js';
import { FHIR_V3_ROLE_CODE_SYSTEM, mapToEvagene } from './relationMap.js';

export interface FhirToIntakeResult {
  readonly family: IntakeFamily;
  readonly warnings: readonly string[];
}

export interface FhirToIntakeOptions {
  readonly patientId: string;
  readonly probandDisplayName?: string;
}

export function fhirBundleToIntakeFamily(
  bundle: unknown,
  options: FhirToIntakeOptions,
): FhirToIntakeResult {
  const resources = readFamilyMemberHistoryResources(bundle);
  const warnings: string[] = [];
  const relatives: Relative[] = [];

  for (const resource of resources) {
    const mapped = mapResource(resource, warnings);
    if (mapped !== undefined) {
      relatives.push(mapped);
    }
  }

  const probandName = (options.probandDisplayName ?? '').trim() || `Patient ${options.patientId}`;
  return {
    family: {
      pedigreeDisplayName: `${probandName}'s family (from FHIR)`,
      proband: { displayName: probandName, biologicalSex: 'unknown' },
      relatives,
    },
    warnings,
  };
}

function mapResource(
  resource: FhirFamilyMemberHistory,
  warnings: string[],
): Relative | undefined {
  const fhirCode = extractV3Code(resource.relationship);
  if (fhirCode === undefined) {
    warnings.push(
      `skipped FamilyMemberHistory ${resource.id ?? '(no id)'}: no v3-RoleCode relationship coding.`,
    );
    return undefined;
  }
  const evageneType = mapToEvagene(fhirCode);
  if (evageneType === undefined) {
    warnings.push(
      `skipped FamilyMemberHistory ${resource.id ?? '(no id)'}: relationship code '${fhirCode}' is not supported.`,
    );
    return undefined;
  }
  return buildRelative(resource, evageneType);
}

function buildRelative(resource: FhirFamilyMemberHistory, relativeType: RelativeType): Relative {
  const displayName = resource.name ?? resource.id ?? 'Unnamed relative';
  const sex = extractSex(resource.sex);
  const year = extractYearOfBirth(resource.bornDate);
  return year === undefined
    ? { relativeType, displayName, biologicalSex: sex }
    : { relativeType, displayName, biologicalSex: sex, yearOfBirth: year };
}

function readFamilyMemberHistoryResources(raw: unknown): readonly FhirFamilyMemberHistory[] {
  if (typeof raw !== 'object' || raw === null) {
    throw new MappingError('FHIR response is not a Bundle with entries.');
  }
  const candidate = raw as Partial<FhirBundle>;
  const entries: readonly FhirBundleEntry[] | undefined = candidate.entry;
  if (candidate.resourceType !== 'Bundle' || entries === undefined) {
    throw new MappingError('FHIR response is not a Bundle with entries.');
  }
  const resources: FhirFamilyMemberHistory[] = [];
  for (const entry of entries) {
    const resource = entry.resource;
    if (resource?.resourceType === 'FamilyMemberHistory') {
      resources.push(resource);
    }
  }
  return resources;
}

function extractV3Code(concept: FhirCodeableConcept | undefined): string | undefined {
  for (const coding of concept?.coding ?? []) {
    if (coding.system === FHIR_V3_ROLE_CODE_SYSTEM) {
      return coding.code;
    }
  }
  return undefined;
}

function extractSex(concept: FhirCodeableConcept | undefined): BiologicalSex {
  for (const coding of concept?.coding ?? []) {
    const code = coding.code;
    if (code === 'female' || code === 'male') {
      return code;
    }
  }
  return 'unknown';
}

function extractYearOfBirth(bornDate: string | undefined): number | undefined {
  if (bornDate === undefined) {
    return undefined;
  }
  const match = /^(\d{4})/.exec(bornDate);
  const captured = match?.[1];
  if (captured === undefined) {
    return undefined;
  }
  return Number.parseInt(captured, 10);
}
