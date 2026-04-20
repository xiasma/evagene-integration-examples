/**
 * Composition root: builds a started-ready Express app from the
 * environment.  One place where concretions meet.
 */

import { ConfigError, type Config, loadConfig } from './config.js';
import { EvageneClient } from './evageneClient.js';
import { EventStore } from './eventStore.js';
import { FetchHttpGateway } from './httpGateway.js';
import { buildServer } from './server.js';
import { SseBroker } from './sseBroker.js';
import { WebhookHandler } from './webhookHandler.js';

export interface BuiltApp {
  readonly config: Config;
  readonly start: () => void;
}

export function buildApp(env: Readonly<Record<string, string | undefined>>): BuiltApp {
  const config = loadConfig(env);
  const store = new EventStore(config.sqlitePath);
  const broker = new SseBroker();
  const handler = new WebhookHandler({
    secret: config.webhookSecret,
    store,
    publisher: broker,
    clock: { nowIso: () => new Date().toISOString() },
  });
  const evagene = new EvageneClient({
    baseUrl: config.baseUrl,
    apiKey: config.apiKey,
    http: new FetchHttpGateway(),
  });
  const server = buildServer({ handler, store, broker, evagene });

  return {
    config,
    start: () => {
      server.listen(config.port, () => {
        process.stdout.write(
          `Clinic referral dashboard listening on http://localhost:${config.port.toString()}/\n`,
        );
      });
    },
  };
}

export { ConfigError };
