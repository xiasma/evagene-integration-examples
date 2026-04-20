/**
 * Composition root: binds concretes to abstractions and hands back an
 * Express app that `main.ts` starts listening on.
 */

import { ConfigError, type Config, loadConfig } from './config.js';
import { EvageneClient } from './evageneClient.js';
import { FetchHttpGateway } from './httpGateway.js';
import { IntakeService } from './intakeService.js';
import { buildServer } from './server.js';

export interface BuiltApp {
  readonly config: Config;
  readonly start: () => void;
}

export function buildApp(env: Readonly<Record<string, string | undefined>>): BuiltApp {
  const config = loadConfig(env);

  const client = new EvageneClient({
    baseUrl: config.baseUrl,
    apiKey: config.apiKey,
    http: new FetchHttpGateway(),
  });
  const service = new IntakeService({ client });
  const server = buildServer({ service, evageneBaseUrl: config.baseUrl });

  return {
    config,
    start: () => {
      server.listen(config.port, () => {
        process.stdout.write(
          `Family-history intake form listening on http://localhost:${config.port.toString()}/\n`,
        );
      });
    },
  };
}

export { ConfigError };
