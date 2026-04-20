/**
 * PedigreeDetail -> FHIR R5 transaction Bundle of FamilyMemberHistory.
 *
 * Pure transformation. Any relative whose relation cannot be mapped
 * produces a warning in `warnings`; the resource is skipped, never
 * fabricated.
 */

import type { FhirBundle, FhirBundleEntry, FhirFamilyMemberHistory } from './fhirTypes.js';
import type { PedigreeDetail, PedigreeIndividual } from './pedigreeDetail.js';
import { mapToFhir } from './relationMap.js';
import { relationsFromProband } from './probandRelations.js';

const ADMIN_GENDER_SYSTEM = 'http://hl7.org/fhir/administrative-gender';

export interface PedigreeMappingResult {
  readonly bundle: FhirBundle;
  readonly probandReference: string;
  readonly warnings: readonly string[];
}

export class MappingError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MappingError';
  }
}

export function pedigreeToFhirBundle(detail: PedigreeDetail): PedigreeMappingResult {
  const relations = relationsFromProband(detail);
  if (relations === undefined) {
    throw new MappingError(
      `Pedigree ${detail.id} has no proband: set one before pushing to FHIR.`,
    );
  }

  const probandReference = `Patient/${relations.proband.id}`;
  const warnings: string[] = [];
  const entries: FhirBundleEntry[] = [];

  for (const view of relations.relatives) {
    const coding = mapToFhir(view.relativeType);
    if (coding === undefined) {
      warnings.push(
        `skipped ${view.individual.displayName}: no FHIR code for relative_type '${view.relativeType}'.`,
      );
      continue;
    }
    entries.push(buildEntry(view.individual, probandReference, coding.code, coding.display));
  }
  for (const unlabelled of relations.unlabelled) {
    warnings.push(
      `skipped ${unlabelled.displayName}: could not derive a supported relation to the proband.`,
    );
  }

  return {
    bundle: { resourceType: 'Bundle', type: 'transaction', entry: entries },
    probandReference,
    warnings,
  };
}

function buildEntry(
  individual: PedigreeIndividual,
  patientReference: string,
  fhirCode: string,
  fhirDisplay: string,
): FhirBundleEntry {
  const resource: FhirFamilyMemberHistory = {
    resourceType: 'FamilyMemberHistory',
    status: 'completed',
    patient: { reference: patientReference },
    name: individual.displayName,
    relationship: {
      coding: [
        {
          system: 'http://terminology.hl7.org/CodeSystem/v3-RoleCode',
          code: fhirCode,
          display: fhirDisplay,
        },
      ],
    },
    sex: {
      coding: [{ system: ADMIN_GENDER_SYSTEM, code: individual.biologicalSex }],
    },
    ...(individual.bornOn === undefined ? {} : { bornDate: individual.bornOn }),
  };
  return {
    fullUrl: `urn:uuid:${individual.id}`,
    resource,
    request: { method: 'POST', url: 'FamilyMemberHistory' },
  };
}
