/**
 * Parses argv + env into a Config value. Two subcommands, one config shape.
 */

const DEFAULT_BASE_URL = 'https://evagene.net';
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export type Mode = 'push' | 'pull';

export interface Config {
  readonly mode: Mode;
  readonly subject: string;
  readonly fhirBaseUrl: string;
  readonly fhirAuthHeader?: string;
  readonly evageneBaseUrl: string;
  readonly evageneApiKey: string;
}

export function loadConfig(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
): Config {
  const parsed = parseArgs(argv);
  const evageneApiKey = (env.EVAGENE_API_KEY ?? '').trim();
  if (!evageneApiKey) {
    throw new ConfigError('EVAGENE_API_KEY environment variable is required.');
  }
  const evageneBaseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;

  if (parsed.mode === 'push' && !UUID_RE.test(parsed.subject)) {
    throw new ConfigError(`pedigree-id must be a UUID, got: ${parsed.subject}`);
  }

  return parsed.fhirAuthHeader === undefined
    ? {
        mode: parsed.mode,
        subject: parsed.subject,
        fhirBaseUrl: parsed.fhirBaseUrl,
        evageneBaseUrl,
        evageneApiKey,
      }
    : {
        mode: parsed.mode,
        subject: parsed.subject,
        fhirBaseUrl: parsed.fhirBaseUrl,
        fhirAuthHeader: parsed.fhirAuthHeader,
        evageneBaseUrl,
        evageneApiKey,
      };
}

interface ParsedArgs {
  readonly mode: Mode;
  readonly subject: string;
  readonly fhirBaseUrl: string;
  readonly fhirAuthHeader?: string;
}

function parseArgs(argv: readonly string[]): ParsedArgs {
  const [command, ...rest] = argv;
  if (command !== 'push' && command !== 'pull') {
    throw new ConfigError(
      `Unknown subcommand '${command ?? ''}'. Expected 'push' or 'pull'.`,
    );
  }
  const flag = command === 'push' ? '--to' : '--from';

  let subject: string | undefined;
  let fhirBaseUrl: string | undefined;
  let fhirAuthHeader: string | undefined;

  let index = 0;
  while (index < rest.length) {
    const token = rest[index] ?? '';
    if (token === flag) {
      fhirBaseUrl = requireFlagValue(rest[index + 1], flag);
      index += 2;
    } else if (token === '--auth-header') {
      fhirAuthHeader = requireFlagValue(rest[index + 1], '--auth-header');
      index += 2;
    } else if (!token.startsWith('--') && subject === undefined) {
      subject = token;
      index += 1;
    } else {
      throw new ConfigError(`Unexpected argument: ${token}`);
    }
  }

  if (subject === undefined) {
    throw new ConfigError(
      command === 'push' ? 'pedigree-id is required' : 'fhir-patient-id is required',
    );
  }
  if (fhirBaseUrl === undefined) {
    throw new ConfigError(`${flag} <fhir-base-url> is required`);
  }

  return fhirAuthHeader === undefined
    ? { mode: command, subject, fhirBaseUrl }
    : { mode: command, subject, fhirBaseUrl, fhirAuthHeader };
}

function requireFlagValue(raw: string | undefined, flag: string): string {
  if (raw === undefined || raw.startsWith('--')) {
    throw new ConfigError(`${flag} requires a value`);
  }
  return raw;
}
