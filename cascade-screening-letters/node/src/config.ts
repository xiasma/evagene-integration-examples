const DEFAULT_BASE_URL = 'https://evagene.net';
const DEFAULT_OUTPUT_DIR = 'letters';
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export { DEFAULT_BASE_URL, DEFAULT_OUTPUT_DIR };

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
  readonly outputDir: string;
  readonly templateId?: string;
  readonly dryRun: boolean;
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
  if (args.templateId !== undefined) {
    requireUuid(args.templateId, '--template');
  }

  const baseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;
  const base = {
    baseUrl,
    apiKey,
    pedigreeId: args.pedigreeId,
    outputDir: args.outputDir,
    dryRun: args.dryRun,
  };
  return args.templateId === undefined ? base : { ...base, templateId: args.templateId };
}

interface ParsedArgs {
  readonly pedigreeId: string;
  readonly outputDir: string;
  readonly templateId?: string;
  readonly dryRun: boolean;
}

function parseArgs(argv: readonly string[]): ParsedArgs {
  let pedigreeId: string | undefined;
  let outputDir = DEFAULT_OUTPUT_DIR;
  let templateId: string | undefined;
  let dryRun = false;

  let index = 0;
  while (index < argv.length) {
    const token = argv[index] ?? '';
    if (token === '--output-dir') {
      outputDir = requireValue(argv, index, '--output-dir');
      index += 2;
    } else if (token === '--template') {
      templateId = requireValue(argv, index, '--template');
      index += 2;
    } else if (token === '--dry-run') {
      dryRun = true;
      index += 1;
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
  const base = { pedigreeId, outputDir, dryRun };
  return templateId === undefined ? base : { ...base, templateId };
}

function requireValue(argv: readonly string[], index: number, label: string): string {
  const value = argv[index + 1];
  if (value === undefined) {
    throw new ConfigError(`${label} requires a value`);
  }
  return value;
}

function requireUuid(value: string, label: string): void {
  if (!UUID_RE.test(value)) {
    throw new ConfigError(`${label} must be a UUID, got: ${value}`);
  }
}
