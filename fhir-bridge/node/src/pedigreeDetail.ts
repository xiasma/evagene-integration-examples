/**
 * Narrow, read-only projection of the Evagene /api/pedigrees/{id}
 * response. Only the fields the bridge actually uses.
 */

export type PedigreeBiologicalSex = 'female' | 'male' | 'unknown';

export interface PedigreeIndividual {
  readonly id: string;
  readonly displayName: string;
  readonly biologicalSex: PedigreeBiologicalSex;
  readonly proband: boolean;
  readonly yearOfBirth?: number;
  readonly bornOn?: string;
}

export interface PedigreeRelationship {
  readonly id: string;
  readonly members: readonly string[];
}

export interface PedigreeEgg {
  readonly individualId: string;
  readonly relationshipId: string;
}

export interface PedigreeDetail {
  readonly id: string;
  readonly displayName: string;
  readonly individuals: readonly PedigreeIndividual[];
  readonly relationships: readonly PedigreeRelationship[];
  readonly eggs: readonly PedigreeEgg[];
}

export class PedigreeParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PedigreeParseError';
  }
}

export function parsePedigreeDetail(raw: unknown): PedigreeDetail {
  const root = requireObject(raw, 'pedigree');
  return {
    id: requireString(root, 'id'),
    displayName: requireString(root, 'display_name'),
    individuals: requireArray(root, 'individuals').map(parseIndividual),
    relationships: requireArray(root, 'relationships').map(parseRelationship),
    eggs: requireArray(root, 'eggs').map(parseEgg),
  };
}

function parseIndividual(raw: unknown): PedigreeIndividual {
  const obj = requireObject(raw, 'individual');
  const props = optionalObject(obj, 'properties') ?? {};
  const year = optionalNumber(props, 'year_of_birth');
  const bornOn = earliestBirthDate(optionalArray(obj, 'events') ?? []);
  return {
    id: requireString(obj, 'id'),
    displayName: requireString(obj, 'display_name'),
    biologicalSex: parseBiologicalSex(requireString(obj, 'biological_sex')),
    proband: parseProbandFlag(obj.proband),
    ...(year === undefined ? {} : { yearOfBirth: year }),
    ...(bornOn === undefined ? {} : { bornOn }),
  };
}

function parseRelationship(raw: unknown): PedigreeRelationship {
  const obj = requireObject(raw, 'relationship');
  return {
    id: requireString(obj, 'id'),
    members: requireArray(obj, 'members').map(m => {
      if (typeof m !== 'string') {
        throw new PedigreeParseError('relationship.members entries must be strings');
      }
      return m;
    }),
  };
}

function parseEgg(raw: unknown): PedigreeEgg {
  const obj = requireObject(raw, 'egg');
  return {
    individualId: requireString(obj, 'individual_id'),
    relationshipId: requireString(obj, 'relationship_id'),
  };
}

function parseBiologicalSex(raw: string): PedigreeBiologicalSex {
  if (raw === 'female' || raw === 'male' || raw === 'unknown') {
    return raw;
  }
  return 'unknown';
}

function parseProbandFlag(raw: unknown): boolean {
  if (raw === 1 || raw === true) {
    return true;
  }
  return false;
}

function earliestBirthDate(events: readonly unknown[]): string | undefined {
  for (const event of events) {
    if (typeof event !== 'object' || event === null) {
      continue;
    }
    const record = event as Record<string, unknown>;
    if (record.type === 'birth' && typeof record.date_start === 'string') {
      return record.date_start;
    }
  }
  return undefined;
}

function requireObject(raw: unknown, label: string): Record<string, unknown> {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
    throw new PedigreeParseError(`Expected object for ${label}`);
  }
  return raw as Record<string, unknown>;
}

function requireString(obj: Record<string, unknown>, key: string): string {
  const value = obj[key];
  if (typeof value !== 'string') {
    throw new PedigreeParseError(`Missing string field '${key}'`);
  }
  return value;
}

function requireArray(obj: Record<string, unknown>, key: string): readonly unknown[] {
  const value = obj[key];
  if (!Array.isArray(value)) {
    throw new PedigreeParseError(`Missing array field '${key}'`);
  }
  return value;
}

function optionalArray(obj: Record<string, unknown>, key: string): readonly unknown[] | undefined {
  const value = obj[key];
  return Array.isArray(value) ? value : undefined;
}

function optionalObject(
  obj: Record<string, unknown>,
  key: string,
): Record<string, unknown> | undefined {
  const value = obj[key];
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}

function optionalNumber(obj: Record<string, unknown>, key: string): number | undefined {
  const value = obj[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}
