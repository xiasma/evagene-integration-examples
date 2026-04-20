/**
 * Domain value objects returned by the LLM extractor.
 * Mirrors the fields the `family-history-intake-form` demo captures so the
 * writer can reuse the same add-relative orchestration.
 */

export type BiologicalSex = 'female' | 'male' | 'unknown';

export type SiblingRelation = 'sister' | 'brother' | 'half_sister' | 'half_brother';

export interface ProbandEntry {
  readonly displayName: string;
  readonly biologicalSex: BiologicalSex;
  readonly yearOfBirth?: number;
  readonly notes?: string;
}

export interface RelativeEntry {
  readonly displayName: string;
  readonly yearOfBirth?: number;
  readonly notes?: string;
}

export interface SiblingEntry {
  readonly displayName: string;
  readonly relation: SiblingRelation;
  readonly yearOfBirth?: number;
  readonly notes?: string;
}

export interface ExtractedFamily {
  readonly proband: ProbandEntry;
  readonly mother?: RelativeEntry;
  readonly father?: RelativeEntry;
  readonly maternalGrandmother?: RelativeEntry;
  readonly maternalGrandfather?: RelativeEntry;
  readonly paternalGrandmother?: RelativeEntry;
  readonly paternalGrandfather?: RelativeEntry;
  readonly siblings: readonly SiblingEntry[];
}

export function siblingBiologicalSex(relation: SiblingRelation): 'female' | 'male' {
  return relation === 'sister' || relation === 'half_sister' ? 'female' : 'male';
}
