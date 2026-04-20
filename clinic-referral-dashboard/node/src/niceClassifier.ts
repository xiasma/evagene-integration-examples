/**
 * Parse the Evagene NICE risk/calculate response into a domain outcome.
 *
 * Strict by design — a silent default would mask a server-side
 * breaking change.  The dashboard only uses the three fields needed
 * to label a card; everything else is ignored.
 */

export type NiceCategory = 'near_population' | 'moderate' | 'high';

export interface NiceOutcome {
  readonly counseleeName: string;
  readonly category: NiceCategory;
  readonly referForGeneticsAssessment: boolean;
}

export class ResponseSchemaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ResponseSchemaError';
  }
}

const KNOWN_CATEGORIES: readonly NiceCategory[] = ['near_population', 'moderate', 'high'];

export function classifyNiceResponse(payload: unknown): NiceOutcome {
  const root = requireObject(payload, 'response');
  const cancerRisk = requireObjectField(root, 'cancer_risk');
  return {
    counseleeName: optionalString(root, 'counselee_name'),
    category: parseCategory(requireStringField(cancerRisk, 'nice_category')),
    referForGeneticsAssessment: requireBooleanField(cancerRisk, 'nice_refer_genetics'),
  };
}

function parseCategory(raw: string): NiceCategory {
  const match = KNOWN_CATEGORIES.find(category => category === raw);
  if (match === undefined) {
    throw new ResponseSchemaError(`Unknown NICE category: ${JSON.stringify(raw)}`);
  }
  return match;
}

function requireObject(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ResponseSchemaError(`${label} is not an object`);
  }
  return value as Record<string, unknown>;
}

function requireObjectField(
  container: Record<string, unknown>,
  key: string,
): Record<string, unknown> {
  return requireObject(container[key], `field '${key}'`);
}

function requireStringField(container: Record<string, unknown>, key: string): string {
  const value = container[key];
  if (typeof value !== 'string') {
    throw new ResponseSchemaError(`field '${key}' is missing or not a string`);
  }
  return value;
}

function requireBooleanField(container: Record<string, unknown>, key: string): boolean {
  const value = container[key];
  if (typeof value !== 'boolean') {
    throw new ResponseSchemaError(`field '${key}' is missing or not a boolean`);
  }
  return value;
}

function optionalString(container: Record<string, unknown>, key: string): string {
  const value = container[key];
  return typeof value === 'string' ? value : '';
}
