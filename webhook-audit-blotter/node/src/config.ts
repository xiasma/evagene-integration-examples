const DEFAULT_PORT = 4000;
const DEFAULT_SQLITE_PATH = './blotter.db';
const MAX_PORT = 65_535;

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export interface Config {
  readonly port: number;
  readonly webhookSecret: string;
  readonly sqlitePath: string;
}

export function loadConfig(env: Readonly<Record<string, string | undefined>>): Config {
  const webhookSecret = (env.EVAGENE_WEBHOOK_SECRET ?? '').trim();
  if (!webhookSecret) {
    throw new ConfigError('EVAGENE_WEBHOOK_SECRET environment variable is required.');
  }
  return {
    port: parsePort(env.PORT),
    webhookSecret,
    sqlitePath: (env.SQLITE_PATH ?? '').trim() || DEFAULT_SQLITE_PATH,
  };
}

function parsePort(raw: string | undefined): number {
  if (raw === undefined || raw.trim() === '') {
    return DEFAULT_PORT;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1 || parsed > MAX_PORT) {
    throw new ConfigError(`PORT must be an integer between 1 and ${MAX_PORT.toString()}; got '${raw}'.`);
  }
  return parsed;
}
