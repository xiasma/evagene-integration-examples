/**
 * The flat proband-plus-relatives shape IntakeService consumes.
 *
 * Kept language-local on purpose: we do not import from the intake-form
 * demo because each demo must be runnable in isolation.
 */

export type BiologicalSex = 'female' | 'male' | 'unknown';

export type RelativeType =
  | 'mother'
  | 'father'
  | 'brother'
  | 'sister'
  | 'half_brother'
  | 'half_sister'
  | 'maternal_grandmother'
  | 'maternal_grandfather'
  | 'paternal_grandmother'
  | 'paternal_grandfather'
  | 'son'
  | 'daughter'
  | 'maternal_aunt'
  | 'maternal_uncle'
  | 'paternal_aunt'
  | 'paternal_uncle'
  | 'niece'
  | 'nephew'
  | 'first_cousin';

export interface Proband {
  readonly displayName: string;
  readonly biologicalSex: BiologicalSex;
  readonly yearOfBirth?: number;
}

export interface Relative {
  readonly relativeType: RelativeType;
  readonly displayName: string;
  readonly biologicalSex: BiologicalSex;
  readonly yearOfBirth?: number;
}

export interface IntakeFamily {
  readonly pedigreeDisplayName: string;
  readonly proband: Proband;
  readonly relatives: readonly Relative[];
}
