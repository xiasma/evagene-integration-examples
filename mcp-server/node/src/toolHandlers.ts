import type {
  AddRelativeArgs,
  CalculateRiskArgs,
  CreateIndividualArgs,
  JsonObject,
} from './evageneClient.js';

export type JsonSchema = Record<string, unknown>;

/**
 * Narrow interface the handlers need.  Defining it structurally lets the
 * concrete `EvageneClient` and the in-memory test fake share a type
 * without forcing either to inherit from the other.
 */
export interface EvageneClientPort {
  listPedigrees(): Promise<JsonObject[]>;
  getPedigree(pedigreeId: string): Promise<JsonObject>;
  describePedigree(pedigreeId: string): Promise<string>;
  listRiskModels(pedigreeId: string): Promise<JsonObject>;
  calculateRisk(args: CalculateRiskArgs): Promise<JsonObject>;
  createIndividual(args: CreateIndividualArgs): Promise<JsonObject>;
  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<JsonObject>;
  addRelative(args: AddRelativeArgs): Promise<JsonObject>;
}

export type ToolHandler = (
  client: EvageneClientPort,
  args: Readonly<Record<string, unknown>>,
) => Promise<unknown>;

export interface ToolSpec {
  readonly name: string;
  readonly description: string;
  readonly inputSchema: JsonSchema;
  readonly handler: ToolHandler;
}

export class ToolArgumentError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ToolArgumentError';
  }
}

// ----------------------------------------------------------------------
// Handlers
// ----------------------------------------------------------------------

const listPedigrees: ToolHandler = async (client) => {
  const pedigrees = await client.listPedigrees();
  return pedigrees.map(summarisePedigree);
};

const getPedigree: ToolHandler = async (client, args) => {
  return client.getPedigree(requireString(args, 'pedigree_id'));
};

const describePedigree: ToolHandler = async (client, args) => {
  const pedigreeId = requireString(args, 'pedigree_id');
  const description = await client.describePedigree(pedigreeId);
  return { pedigree_id: pedigreeId, description };
};

const listRiskModels: ToolHandler = async (client, args) => {
  return client.listRiskModels(requireString(args, 'pedigree_id'));
};

const calculateRisk: ToolHandler = async (client, args) => {
  const pedigreeId = requireString(args, 'pedigree_id');
  const model = requireString(args, 'model');
  const counseleeId = optionalString(args, 'counselee_id');
  return client.calculateRisk(
    counseleeId === undefined
      ? { pedigreeId, model }
      : { pedigreeId, model, counseleeId },
  );
};

const addIndividual: ToolHandler = async (client, args) => {
  const pedigreeId = requireString(args, 'pedigree_id');
  const individual = await client.createIndividual({
    displayName: requireString(args, 'display_name'),
    biologicalSex: requireString(args, 'biological_sex'),
  });
  const individualId = requireString(individual, 'id');
  await client.addIndividualToPedigree(pedigreeId, individualId);
  return { pedigree_id: pedigreeId, individual };
};

const addRelative: ToolHandler = async (client, args) => {
  const pedigreeId = requireString(args, 'pedigree_id');
  const relativeOf = requireString(args, 'relative_of');
  const relativeType = requireString(args, 'relative_type');
  const displayName = optionalString(args, 'display_name');
  const biologicalSex = optionalString(args, 'biological_sex');

  const base: AddRelativeArgs = { pedigreeId, relativeOf, relativeType };
  const withName: AddRelativeArgs =
    displayName === undefined ? base : { ...base, displayName };
  const withSex: AddRelativeArgs =
    biologicalSex === undefined ? withName : { ...withName, biologicalSex };
  return client.addRelative(withSex);
};

// ----------------------------------------------------------------------
// Tool catalogue
// ----------------------------------------------------------------------

const PEDIGREE_ID_SCHEMA: JsonSchema = {
  type: 'string',
  description: 'UUID of the pedigree.',
};

const BIOLOGICAL_SEX_SCHEMA: JsonSchema = {
  type: 'string',
  enum: ['male', 'female', 'unknown'],
  description: 'Biological sex of the individual.',
};

export const TOOL_SPECS: readonly ToolSpec[] = [
  {
    name: 'list_pedigrees',
    description: 'List all pedigrees owned by the authenticated user.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    handler: listPedigrees,
  },
  {
    name: 'get_pedigree',
    description: 'Fetch the full pedigree detail — individuals, relationships, eggs, diseases.',
    inputSchema: {
      type: 'object',
      properties: { pedigree_id: PEDIGREE_ID_SCHEMA },
      required: ['pedigree_id'],
      additionalProperties: false,
    },
    handler: getPedigree,
  },
  {
    name: 'describe_pedigree',
    description:
      'Generate a structured English description of the pedigree, suitable for clinical reasoning.',
    inputSchema: {
      type: 'object',
      properties: { pedigree_id: PEDIGREE_ID_SCHEMA },
      required: ['pedigree_id'],
      additionalProperties: false,
    },
    handler: describePedigree,
  },
  {
    name: 'list_risk_models',
    description:
      'List the risk models available for this pedigree (e.g. NICE, TYRER_CUZICK, BRCAPRO).',
    inputSchema: {
      type: 'object',
      properties: { pedigree_id: PEDIGREE_ID_SCHEMA },
      required: ['pedigree_id'],
      additionalProperties: false,
    },
    handler: listRiskModels,
  },
  {
    name: 'calculate_risk',
    description: 'Run a named risk model against the pedigree and return the structured result.',
    inputSchema: {
      type: 'object',
      properties: {
        pedigree_id: PEDIGREE_ID_SCHEMA,
        model: {
          type: 'string',
          description:
            'Risk-model enum, e.g. NICE, TYRER_CUZICK, CLAUS, BRCAPRO, AUTOSOMAL_DOMINANT.',
        },
        counselee_id: {
          type: 'string',
          description: 'Optional UUID of the target individual; defaults to the proband.',
        },
      },
      required: ['pedigree_id', 'model'],
      additionalProperties: false,
    },
    handler: calculateRisk,
  },
  {
    name: 'add_individual',
    description:
      'Create a new individual and attach them to the pedigree. Returns the stored individual.',
    inputSchema: {
      type: 'object',
      properties: {
        pedigree_id: PEDIGREE_ID_SCHEMA,
        display_name: { type: 'string', description: 'Human-readable name.' },
        biological_sex: BIOLOGICAL_SEX_SCHEMA,
      },
      required: ['pedigree_id', 'display_name', 'biological_sex'],
      additionalProperties: false,
    },
    handler: addIndividual,
  },
  {
    name: 'add_relative',
    description:
      'Add a new individual related to an existing one by kinship type (father, sister, cousin, etc.).',
    inputSchema: {
      type: 'object',
      properties: {
        pedigree_id: PEDIGREE_ID_SCHEMA,
        relative_of: {
          type: 'string',
          description: 'UUID of the existing individual whose relative is being added.',
        },
        relative_type: {
          type: 'string',
          description:
            'Kinship enum: father, mother, son, daughter, brother, sister, half_brother, half_sister, ' +
            'paternal_grandfather, paternal_grandmother, maternal_grandfather, maternal_grandmother, ' +
            'grandson, granddaughter, paternal_uncle, paternal_aunt, maternal_uncle, maternal_aunt, ' +
            'nephew, niece, first_cousin, partner, step_father, step_mother, unrelated.',
        },
        display_name: {
          type: 'string',
          description: 'Optional human-readable name for the new individual.',
        },
        biological_sex: BIOLOGICAL_SEX_SCHEMA,
      },
      required: ['pedigree_id', 'relative_of', 'relative_type'],
      additionalProperties: false,
    },
    handler: addRelative,
  },
];

const TOOLS_BY_NAME = new Map<string, ToolSpec>(
  TOOL_SPECS.map((spec) => [spec.name, spec] as const),
);

export async function handleCall(
  client: EvageneClientPort,
  name: string,
  args: Readonly<Record<string, unknown>>,
): Promise<unknown> {
  const spec = TOOLS_BY_NAME.get(name);
  if (spec === undefined) {
    throw new ToolArgumentError(`Unknown tool: ${name}`);
  }
  return spec.handler(client, args);
}

// ----------------------------------------------------------------------
// Argument helpers
// ----------------------------------------------------------------------

function requireString(source: Readonly<Record<string, unknown>>, key: string): string {
  const value = source[key];
  if (typeof value !== 'string' || value === '') {
    throw new ToolArgumentError(`Missing or empty string field: ${JSON.stringify(key)}`);
  }
  return value;
}

function optionalString(
  source: Readonly<Record<string, unknown>>,
  key: string,
): string | undefined {
  const value = source[key];
  if (value === undefined || value === null) return undefined;
  if (typeof value !== 'string') {
    throw new ToolArgumentError(`Field ${JSON.stringify(key)} must be a string when provided`);
  }
  return value === '' ? undefined : value;
}

function summarisePedigree(item: JsonObject): JsonObject {
  return {
    id: item.id,
    display_name: item.display_name,
    date_represented: item.date_represented,
    disease_ids: item.disease_ids ?? [],
  };
}
