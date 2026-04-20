const DEFAULT_BASE_URL = 'https://evagene.net';
const DEFAULT_LABEL = 'Family pedigree';
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export interface Config {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly pedigreeId: string;
  readonly nameSuffix?: string;
  readonly label: string;
}

export function loadConfig(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
): Config {
  const args = parseArgs(argv);
  const apiKey = (env.EVAGENE_API_KEY ?? '').trim();
  if (!apiKey) {
    throw new ConfigError('EVAGENE_API_KEY environment variable is required.');
  }

  requireUuid(args.pedigreeId, 'pedigree-id');
  const baseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;

  return {
    baseUrl,
    apiKey,
    pedigreeId: args.pedigreeId,
    label: args.label ?? DEFAULT_LABEL,
    ...(args.nameSuffix !== undefined ? { nameSuffix: args.nameSuffix } : {}),
  };
}

interface ParsedArgs {
  readonly pedigreeId: string;
  readonly nameSuffix?: string;
  readonly label?: string;
}

function parseArgs(argv: readonly string[]): ParsedArgs {
  let pedigreeId: string | undefined;
  let nameSuffix: string | undefined;
  let label: string | undefined;

  let index = 0;
  while (index < argv.length) {
    const token = argv[index] ?? '';
    if (token === '--name') {
      nameSuffix = requireValue(argv, index, '--name');
      index += 2;
    } else if (token === '--label') {
      label = requireValue(argv, index, '--label');
      index += 2;
    } else if (!token.startsWith('--') && pedigreeId === undefined) {
      pedigreeId = token;
      index += 1;
    } else {
      throw new ConfigError(`Unexpected argument: ${token}`);
    }
  }

  if (pedigreeId === undefined) {
    throw new ConfigError('pedigree-id is required');
  }

  const args: {
    pedigreeId: string;
    nameSuffix?: string;
    label?: string;
  } = { pedigreeId };
  if (nameSuffix !== undefined) args.nameSuffix = nameSuffix;
  if (label !== undefined) args.label = label;
  return args;
}

function requireValue(argv: readonly string[], index: number, flag: string): string {
  const value = argv[index + 1];
  if (value === undefined) {
    throw new ConfigError(`${flag} requires a value`);
  }
  return value;
}

function requireUuid(value: string, label: string): void {
  if (!UUID_RE.test(value)) {
    throw new ConfigError(`${label} must be a UUID, got: ${value}`);
  }
}
