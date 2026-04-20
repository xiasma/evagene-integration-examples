const DEFAULT_BASE_URL = 'https://evagene.net';

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export interface Config {
  readonly baseUrl: string;
  readonly apiKey: string;
}

/**
 * Read the server's configuration from the supplied environment.
 *
 * The MCP server is launched by a client (Claude Desktop, Cursor, etc.)
 * which injects `EVAGENE_API_KEY` via the config stanza — there are no
 * command-line arguments to parse.
 */
export function loadConfig(env: Readonly<Record<string, string | undefined>>): Config {
  const apiKey = (env.EVAGENE_API_KEY ?? '').trim();
  if (!apiKey) {
    throw new ConfigError('EVAGENE_API_KEY environment variable is required.');
  }

  const baseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;
  return { baseUrl, apiKey };
}
