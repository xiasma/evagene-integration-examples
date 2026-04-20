/**
 * Composition root: build a ready-to-start Express app from the
 * environment. The only place concretes are bound to abstractions.
 */

import { ConfigError, type Config, loadConfig } from './config.js';
import { EvageneClient } from './evageneClient.js';
import { FetchHttpGateway } from './httpGateway.js';
import { SlackHandler, TeamsHandler } from './handlers.js';
import { buildServer } from './server.js';

export interface BuiltApp {
  readonly config: Config;
  readonly start: () => void;
}

export function buildApp(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
): BuiltApp {
  const config = loadConfig(argv, env);

  const api = new EvageneClient({
    baseUrl: config.baseUrl,
    apiKey: config.apiKey,
    http: new FetchHttpGateway(),
  });

  const clock = { nowSeconds: (): number => Math.floor(Date.now() / 1000) };
  const slackHandler = config.slackSigningSecret === undefined
    ? undefined
    : new SlackHandler({ signingSecret: config.slackSigningSecret, api, clock });
  const teamsHandler = config.teamsSigningSecret === undefined
    ? undefined
    : new TeamsHandler({ signingSecret: config.teamsSigningSecret, api });

  const server = buildServer({ slackHandler, teamsHandler });

  return {
    config,
    start: (): void => {
      server.listen(config.port, () => {
        process.stdout.write(
          `Chat-bot listening on http://localhost:${config.port.toString()}/\n`,
        );
      });
    },
  };
}

export { ConfigError };
