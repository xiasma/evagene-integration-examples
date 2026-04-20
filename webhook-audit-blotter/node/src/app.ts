/**
 * Composition root: builds a started-ready Express app from the
 * environment.  One place where concretions meet.
 */

import { ConfigError, type Config, loadConfig } from './config.js';
import { EventStore } from './eventStore.js';
import { buildServer } from './server.js';
import { WebhookHandler } from './webhookHandler.js';

export interface BuiltApp {
  readonly config: Config;
  readonly start: () => void;
}

export function buildApp(env: Readonly<Record<string, string | undefined>>): BuiltApp {
  const config = loadConfig(env);
  const store = new EventStore(config.sqlitePath);
  const handler = new WebhookHandler({
    secret: config.webhookSecret,
    store,
    clock: { nowIso: () => new Date().toISOString() },
  });
  const server = buildServer({ handler, store });

  return {
    config,
    start: () => {
      server.listen(config.port, () => {
        process.stdout.write(
          `Webhook audit blotter listening on http://localhost:${config.port.toString()}/\n`,
        );
      });
    },
  };
}

export { ConfigError };
