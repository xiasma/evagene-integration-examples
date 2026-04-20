const DEFAULT_BASE_URL = 'https://evagene.net';
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
  readonly counseleeId?: string;
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
  if (args.counseleeId !== undefined) {
    requireUuid(args.counseleeId, '--counselee');
  }

  const baseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;
  return args.counseleeId === undefined
    ? { baseUrl, apiKey, pedigreeId: args.pedigreeId }
    : { baseUrl, apiKey, pedigreeId: args.pedigreeId, counseleeId: args.counseleeId };
}

interface ParsedArgs {
  readonly pedigreeId: string;
  readonly counseleeId?: string;
}

function parseArgs(argv: readonly string[]): ParsedArgs {
  let pedigreeId: string | undefined;
  let counseleeId: string | undefined;

  let index = 0;
  while (index < argv.length) {
    const token = argv[index] ?? '';
    if (token === '--counselee') {
      const value = argv[index + 1];
      if (value === undefined) {
        throw new ConfigError('--counselee requires a value');
      }
      counseleeId = value;
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
  return counseleeId === undefined ? { pedigreeId } : { pedigreeId, counseleeId };
}

function requireUuid(value: string, label: string): void {
  if (!UUID_RE.test(value)) {
    throw new ConfigError(`${label} must be a UUID, got: ${value}`);
  }
}
