/**
 * The subset of FHIR R5 Bundle and FamilyMemberHistory shapes used by
 * the bridge. Anything the bridge doesn't read or write is omitted.
 *
 * Spec: https://hl7.org/fhir/R5/familymemberhistory.html
 *       https://hl7.org/fhir/R5/bundle.html
 */

export interface FhirCoding {
  readonly system: string;
  readonly code: string;
  readonly display?: string;
}

export interface FhirCodeableConcept {
  readonly coding?: readonly FhirCoding[];
  readonly text?: string;
}

export interface FhirReference {
  readonly reference: string;
}

export interface FhirFamilyMemberHistory {
  readonly resourceType: 'FamilyMemberHistory';
  readonly id?: string;
  readonly status: 'partial' | 'completed' | 'entered-in-error' | 'health-unknown';
  readonly patient: FhirReference;
  readonly name?: string;
  readonly relationship: FhirCodeableConcept;
  readonly sex?: FhirCodeableConcept;
  readonly bornDate?: string;
}

export interface FhirBundleEntry {
  readonly fullUrl?: string;
  readonly resource?: FhirFamilyMemberHistory;
  readonly request?: {
    readonly method: 'POST' | 'PUT';
    readonly url: string;
  };
  readonly response?: {
    readonly status: string;
    readonly location?: string;
  };
}

export type FhirBundleType = 'transaction' | 'transaction-response' | 'searchset' | 'collection';

export interface FhirBundle {
  readonly resourceType: 'Bundle';
  readonly type: FhirBundleType;
  readonly entry?: readonly FhirBundleEntry[];
}
