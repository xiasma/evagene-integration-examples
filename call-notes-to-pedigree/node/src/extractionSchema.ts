/**
 * JSON schema the LLM tool is asked to fill, and the pure parser that
 * turns a conforming tool-use input into an {@link ExtractedFamily}.
 * Tests exercise schema + parser without any LLM involvement.
 */

import type {
  BiologicalSex,
  ExtractedFamily,
  ProbandEntry,
  RelativeEntry,
  SiblingEntry,
  SiblingRelation,
} from './extractedFamily.js';

export const TOOL_NAME = 'record_extracted_family';

export const TOOL_DESCRIPTION =
  'Record the first- and second-degree relatives you were able to identify in the ' +
  'transcript. Only include a relative if the transcript mentions them. Keep names ' +
  "as given. Put any disease, diagnosis, age-at-diagnosis or death details in the " +
  "relative's 'notes' field in plain prose -- do not invent structure for them.";

export const SYSTEM_PROMPT =
  'You are a family-history extraction assistant for genetic counselling. ' +
  'Read the transcript and call the record_extracted_family tool exactly once ' +
  'with the family structure you can identify. ' +
  'Include the proband and, when mentioned, the mother, father, four grandparents, ' +
  'and full or half siblings. ' +
  'If a relative is not mentioned, omit them rather than guessing. ' +
  "Put disease history, ages at diagnosis, and any free-text context into the " +
  "per-relative 'notes' field. " +
  "If a year of birth is stated or can be inferred directly (for example from " +
  "'she is 42' in a session dated this year), fill year_of_birth; otherwise leave " +
  'it null.';

const BIOLOGICAL_SEXES: readonly BiologicalSex[] = ['female', 'male', 'unknown'];
const SIBLING_RELATIONS: readonly SiblingRelation[] = [
  'sister',
  'brother',
  'half_sister',
  'half_brother',
];

const MIN_YEAR = 1850;
const MAX_YEAR = 2030;

export class ExtractionSchemaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ExtractionSchemaError';
  }
}

export interface ToolSchema {
  readonly name: string;
  readonly description: string;
  readonly input_schema: {
    readonly type: 'object';
    readonly properties: Record<string, unknown>;
    readonly required: string[];
    readonly additionalProperties: false;
  };
}

export function buildToolSchema(): ToolSchema {
  return {
    name: TOOL_NAME,
    description: TOOL_DESCRIPTION,
    input_schema: {
      type: 'object',
      additionalProperties: false,
      required: ['proband', 'siblings'],
      properties: {
        proband: probandSchema(),
        mother: relativeSchema(),
        father: relativeSchema(),
        maternal_grandmother: relativeSchema(),
        maternal_grandfather: relativeSchema(),
        paternal_grandmother: relativeSchema(),
        paternal_grandfather: relativeSchema(),
        siblings: { type: 'array', items: siblingSchema() },
      },
    },
  };
}

export function parseExtraction(payload: unknown): ExtractedFamily {
  const obj = requireObject(payload, 'root');
  return {
    proband: parseProband(requireObject(obj.proband, 'proband')),
    ...optionalRelative(obj.mother, 'mother'),
    ...optionalRelative(obj.father, 'father'),
    ...optionalRelative(obj.maternal_grandmother, 'maternalGrandmother'),
    ...optionalRelative(obj.maternal_grandfather, 'maternalGrandfather'),
    ...optionalRelative(obj.paternal_grandmother, 'paternalGrandmother'),
    ...optionalRelative(obj.paternal_grandfather, 'paternalGrandfather'),
    siblings: parseSiblings(obj.siblings),
  };
}

function probandSchema(): Record<string, unknown> {
  return {
    type: 'object',
    additionalProperties: false,
    required: ['display_name', 'biological_sex'],
    properties: {
      display_name: { type: 'string' },
      biological_sex: { type: 'string', enum: BIOLOGICAL_SEXES },
      year_of_birth: nullableYear(),
      notes: nullableString(),
    },
  };
}

function relativeSchema(): Record<string, unknown> {
  return {
    type: 'object',
    additionalProperties: false,
    required: ['display_name'],
    properties: {
      display_name: { type: 'string' },
      year_of_birth: nullableYear(),
      notes: nullableString(),
    },
  };
}

function siblingSchema(): Record<string, unknown> {
  return {
    type: 'object',
    additionalProperties: false,
    required: ['display_name', 'relation'],
    properties: {
      display_name: { type: 'string' },
      relation: { type: 'string', enum: SIBLING_RELATIONS },
      year_of_birth: nullableYear(),
      notes: nullableString(),
    },
  };
}

function nullableYear(): Record<string, unknown> {
  return { type: ['integer', 'null'], minimum: MIN_YEAR, maximum: MAX_YEAR };
}

function nullableString(): Record<string, unknown> {
  return { type: ['string', 'null'] };
}

function parseProband(payload: Record<string, unknown>): ProbandEntry {
  const base = {
    displayName: requireNonEmptyString(payload, 'display_name'),
    biologicalSex: parseBiologicalSex(requireString(payload, 'biological_sex')),
  } as const;
  const year = optionalYear(payload, 'year_of_birth');
  const notes = optionalString(payload, 'notes');
  return {
    ...base,
    ...(year !== undefined ? { yearOfBirth: year } : {}),
    ...(notes !== undefined ? { notes } : {}),
  };
}

function optionalRelative(
  payload: unknown,
  fieldName: string,
): Record<string, RelativeEntry> {
  if (payload === undefined || payload === null) {
    return {};
  }
  const obj = requireObject(payload, fieldName);
  const year = optionalYear(obj, 'year_of_birth');
  const notes = optionalString(obj, 'notes');
  const entry: RelativeEntry = {
    displayName: requireNonEmptyString(obj, 'display_name'),
    ...(year !== undefined ? { yearOfBirth: year } : {}),
    ...(notes !== undefined ? { notes } : {}),
  };
  return { [fieldName]: entry };
}

function parseSiblings(payload: unknown): readonly SiblingEntry[] {
  if (payload === undefined || payload === null) {
    return [];
  }
  if (!Array.isArray(payload)) {
    throw new ExtractionSchemaError("Field 'siblings' must be an array.");
  }
  return payload.map(parseSibling);
}

function parseSibling(raw: unknown): SiblingEntry {
  const obj = requireObject(raw, 'sibling');
  const year = optionalYear(obj, 'year_of_birth');
  const notes = optionalString(obj, 'notes');
  return {
    displayName: requireNonEmptyString(obj, 'display_name'),
    relation: parseSiblingRelation(requireString(obj, 'relation')),
    ...(year !== undefined ? { yearOfBirth: year } : {}),
    ...(notes !== undefined ? { notes } : {}),
  };
}

function parseBiologicalSex(raw: string): BiologicalSex {
  const match = BIOLOGICAL_SEXES.find(sex => sex === raw);
  if (match === undefined) {
    throw new ExtractionSchemaError(`Unknown biological_sex: '${raw}'`);
  }
  return match;
}

function parseSiblingRelation(raw: string): SiblingRelation {
  const match = SIBLING_RELATIONS.find(rel => rel === raw);
  if (match === undefined) {
    throw new ExtractionSchemaError(`Unknown sibling relation: '${raw}'`);
  }
  return match;
}

function requireObject(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ExtractionSchemaError(`Expected object for '${label}'.`);
  }
  return value as Record<string, unknown>;
}

function requireString(obj: Record<string, unknown>, key: string): string {
  const value = obj[key];
  if (typeof value !== 'string') {
    throw new ExtractionSchemaError(`Missing required string field '${key}'.`);
  }
  return value;
}

function requireNonEmptyString(obj: Record<string, unknown>, key: string): string {
  const value = requireString(obj, key).trim();
  if (value === '') {
    throw new ExtractionSchemaError(`Field '${key}' must be a non-empty string.`);
  }
  return value;
}

function optionalYear(obj: Record<string, unknown>, key: string): number | undefined {
  const value = obj[key];
  if (value === undefined || value === null) {
    return undefined;
  }
  if (typeof value !== 'number' || !Number.isInteger(value)) {
    throw new ExtractionSchemaError(`Field '${key}' must be an integer or null.`);
  }
  return value;
}

function optionalString(obj: Record<string, unknown>, key: string): string | undefined {
  const value = obj[key];
  if (value === undefined || value === null) {
    return undefined;
  }
  if (typeof value !== 'string') {
    throw new ExtractionSchemaError(`Field '${key}' must be a string or null.`);
  }
  const trimmed = value.trim();
  return trimmed === '' ? undefined : trimmed;
}
