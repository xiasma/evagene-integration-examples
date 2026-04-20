const DEFAULT_BASE_URL = 'https://evagene.net';
const DEFAULT_PORT = 3000;

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
}

export function loadConfig(env: Readonly<Record<string, string | undefined>>): Config {
  const apiKey = (env.EVAGENE_API_KEY ?? '').trim();
  if (!apiKey) {
    throw new ConfigError('EVAGENE_API_KEY environment variable is required.');
  }
  const baseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;
  const port = parsePort(env.PORT);
  return { baseUrl, apiKey, port };
}

function parsePort(raw: string | undefined): number {
  if (raw === undefined || raw.trim() === '') {
    return DEFAULT_PORT;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1 || parsed > 65_535) {
    throw new ConfigError(`PORT must be an integer between 1 and 65535; got '${raw}'.`);
  }
  return parsed;
}
