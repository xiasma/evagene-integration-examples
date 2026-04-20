/**
 * Domain value object + parser for the intake form's submission.
 *
 * Pure: takes a raw form body (as Express populates it via urlencoded)
 * and returns either a validated IntakeSubmission or throws an
 * IntakeValidationError naming the field at fault.
 */

export type BiologicalSex = 'female' | 'male' | 'unknown';

export type SiblingRelation = 'sister' | 'brother' | 'half_sister' | 'half_brother';

export interface RelativeEntry {
  readonly displayName: string;
  readonly yearOfBirth?: number;
}

export interface SiblingEntry extends RelativeEntry {
  readonly relation: SiblingRelation;
  readonly biologicalSex: BiologicalSex;
}

export interface IntakeSubmission {
  readonly proband: {
    readonly displayName: string;
    readonly biologicalSex: BiologicalSex;
    readonly yearOfBirth?: number;
  };
  readonly mother?: RelativeEntry;
  readonly father?: RelativeEntry;
  readonly maternalGrandmother?: RelativeEntry;
  readonly maternalGrandfather?: RelativeEntry;
  readonly paternalGrandmother?: RelativeEntry;
  readonly paternalGrandfather?: RelativeEntry;
  readonly siblings: readonly SiblingEntry[];
}

export class IntakeValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'IntakeValidationError';
  }
}

const MIN_YEAR = 1850;
const MAX_YEAR = 2030;
const MAX_SIBLINGS = 4;
const KNOWN_SEXES: readonly BiologicalSex[] = ['female', 'male', 'unknown'];
const KNOWN_SIBLING_RELATIONS: readonly SiblingRelation[] = [
  'sister',
  'brother',
  'half_sister',
  'half_brother',
];

export function parseIntakeSubmission(body: Record<string, unknown>): IntakeSubmission {
  const probandName = requireNonEmpty(body, 'proband_name', "The patient's name");
  const probandSex = parseSex(optionalString(body, 'proband_sex'));
  const probandYear = parseYear(optionalString(body, 'proband_year'), 'proband_year');

  return {
    proband: {
      displayName: probandName,
      biologicalSex: probandSex,
      ...(probandYear !== undefined ? { yearOfBirth: probandYear } : {}),
    },
    ...optionalRelative(body, 'mother', 'mother'),
    ...optionalRelative(body, 'father', 'father'),
    ...optionalRelative(body, 'maternal_grandmother', 'maternalGrandmother'),
    ...optionalRelative(body, 'maternal_grandfather', 'maternalGrandfather'),
    ...optionalRelative(body, 'paternal_grandmother', 'paternalGrandmother'),
    ...optionalRelative(body, 'paternal_grandfather', 'paternalGrandfather'),
    siblings: parseSiblings(body),
  };
}

function optionalRelative(
  body: Record<string, unknown>,
  formPrefix: string,
  fieldName: string,
): Record<string, RelativeEntry> {
  const name = optionalString(body, `${formPrefix}_name`).trim();
  if (name === '') {
    return {};
  }
  const year = parseYear(optionalString(body, `${formPrefix}_year`), `${formPrefix}_year`);
  const entry: RelativeEntry = year === undefined ? { displayName: name } : { displayName: name, yearOfBirth: year };
  return { [fieldName]: entry };
}

function parseSiblings(body: Record<string, unknown>): readonly SiblingEntry[] {
  const siblings: SiblingEntry[] = [];
  for (let index = 0; index < MAX_SIBLINGS; index += 1) {
    const name = optionalString(body, `sibling_${index.toString()}_name`).trim();
    if (name === '') {
      continue;
    }
    const relation = parseSiblingRelation(
      optionalString(body, `sibling_${index.toString()}_relation`),
      index,
    );
    const year = parseYear(
      optionalString(body, `sibling_${index.toString()}_year`),
      `sibling_${index.toString()}_year`,
    );
    siblings.push({
      displayName: name,
      relation,
      biologicalSex: sexForSiblingRelation(relation),
      ...(year !== undefined ? { yearOfBirth: year } : {}),
    });
  }
  return siblings;
}

function parseSex(raw: string): BiologicalSex {
  if (raw === '') {
    return 'unknown';
  }
  const match = KNOWN_SEXES.find(known => known === raw);
  if (match === undefined) {
    throw new IntakeValidationError(`Unknown biological sex: ${raw}`);
  }
  return match;
}

function parseSiblingRelation(raw: string, index: number): SiblingRelation {
  const match = KNOWN_SIBLING_RELATIONS.find(known => known === raw);
  if (match === undefined) {
    throw new IntakeValidationError(
      `Sibling ${(index + 1).toString()} must have a relation (sister / brother / half_sister / half_brother).`,
    );
  }
  return match;
}

function sexForSiblingRelation(relation: SiblingRelation): BiologicalSex {
  return relation === 'sister' || relation === 'half_sister' ? 'female' : 'male';
}

function parseYear(raw: string, fieldName: string): number | undefined {
  const trimmed = raw.trim();
  if (trimmed === '') {
    return undefined;
  }
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || parsed < MIN_YEAR || parsed > MAX_YEAR) {
    throw new IntakeValidationError(
      `Field '${fieldName}' must be a year between ${MIN_YEAR.toString()} and ${MAX_YEAR.toString()}.`,
    );
  }
  return parsed;
}

function requireNonEmpty(body: Record<string, unknown>, key: string, label: string): string {
  const value = optionalString(body, key).trim();
  if (value === '') {
    throw new IntakeValidationError(`${label} is required.`);
  }
  return value;
}

function optionalString(body: Record<string, unknown>, key: string): string {
  const value = body[key];
  return typeof value === 'string' ? value : '';
}
