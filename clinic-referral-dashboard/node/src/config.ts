const DEFAULT_PORT = 4000;
const DEFAULT_BASE_URL = 'https://evagene.net';
const DEFAULT_SQLITE_PATH = './dashboard.db';
const MAX_PORT = 65_535;

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export interface Config {
  readonly port: number;
  readonly apiKey: string;
  readonly webhookSecret: string;
  readonly baseUrl: string;
  readonly sqlitePath: string;
}

export function loadConfig(env: Readonly<Record<string, string | undefined>>): Config {
  return {
    port: parsePort(env.PORT),
    apiKey: requireEnv(env, 'EVAGENE_API_KEY'),
    webhookSecret: requireEnv(env, 'EVAGENE_WEBHOOK_SECRET'),
    baseUrl: (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL,
    sqlitePath: (env.SQLITE_PATH ?? '').trim() || DEFAULT_SQLITE_PATH,
  };
}

function requireEnv(env: Readonly<Record<string, string | undefined>>, name: string): string {
  const value = (env[name] ?? '').trim();
  if (!value) {
    throw new ConfigError(`${name} environment variable is required.`);
  }
  return value;
}

function parsePort(raw: string | undefined): number {
  if (raw === undefined || raw.trim() === '') {
    return DEFAULT_PORT;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1 || parsed > MAX_PORT) {
    throw new ConfigError(
      `PORT must be an integer between 1 and ${MAX_PORT.toString()}; got '${raw}'.`,
    );
  }
  return parsed;
}
