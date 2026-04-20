/**
 * Immutable configuration loaded from argv + env.
 *
 * At least one of slackSigningSecret / teamsSigningSecret must be set -
 * a bot with neither route enabled has nothing to do.
 */

const DEFAULT_BASE_URL = 'https://evagene.net';
const DEFAULT_PORT = 3000;
const MAX_PORT = 65_535;

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export interface Config {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly port: number;
  readonly slackSigningSecret: string | undefined;
  readonly teamsSigningSecret: string | undefined;
}

export function loadConfig(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
): Config {
  const apiKey = trimmed(env.EVAGENE_API_KEY);
  if (apiKey === undefined) {
    throw new ConfigError('EVAGENE_API_KEY environment variable is required.');
  }
  const slack = trimmed(env.SLACK_SIGNING_SECRET);
  const teams = trimmed(env.TEAMS_SIGNING_SECRET);
  if (slack === undefined && teams === undefined) {
    throw new ConfigError(
      'At least one of SLACK_SIGNING_SECRET or TEAMS_SIGNING_SECRET must be set.',
    );
  }
  return {
    baseUrl: trimmed(env.EVAGENE_BASE_URL) ?? DEFAULT_BASE_URL,
    apiKey,
    port: parsePort(argv, env.PORT),
    slackSigningSecret: slack,
    teamsSigningSecret: teams,
  };
}

function parsePort(argv: readonly string[], rawEnv: string | undefined): number {
  const rawArg = readPortFlag(argv);
  const raw = rawArg ?? rawEnv;
  if (raw === undefined || raw.trim() === '') {
    return DEFAULT_PORT;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1 || parsed > MAX_PORT) {
    throw new ConfigError(`PORT must be an integer between 1 and ${MAX_PORT.toString()}; got '${raw}'.`);
  }
  return parsed;
}

function readPortFlag(argv: readonly string[]): string | undefined {
  let index = 0;
  while (index < argv.length) {
    const token = argv[index] ?? '';
    if (token === '--port') {
      const value = argv[index + 1];
      if (value === undefined) {
        throw new ConfigError('--port requires a value');
      }
      return value;
    }
    if (token.startsWith('--port=')) {
      return token.slice('--port='.length);
    }
    if (token.startsWith('--')) {
      throw new ConfigError(`Unexpected argument: ${token}`);
    }
    index += 1;
  }
  return undefined;
}

function trimmed(raw: string | undefined): string | undefined {
  if (raw === undefined) {
    return undefined;
  }
  const value = raw.trim();
  return value === '' ? undefined : value;
}
