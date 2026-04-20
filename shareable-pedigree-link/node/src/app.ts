import { type Clock, SystemClock } from './clock.js';
import { ConfigError, type Config, loadConfig } from './config.js';
import { ApiError, EvageneClient, type MintedKey } from './evageneClient.js';
import { FetchHttpGateway, type HttpGateway } from './httpGateway.js';
import { buildKeyName } from './keyName.js';
import { type TextSink, present } from './presenter.js';
import { buildSnippet } from './snippetBuilder.js';

export const EXIT_OK = 0;
export const EXIT_USAGE = 64;
export const EXIT_UNAVAILABLE = 69;

const RATE_PER_MINUTE = 60;
const RATE_PER_DAY = 1000;

export interface Streams {
  readonly stdout: TextSink;
  readonly stderr: TextSink;
}

export interface Dependencies {
  readonly gateway: HttpGateway;
  readonly clock: Clock;
}

export async function run(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
  streams: Streams,
  deps: Dependencies = defaultDependencies(),
): Promise<number> {
  let config: Config;
  try {
    config = loadConfig(argv, env);
  } catch (error) {
    if (error instanceof ConfigError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_USAGE;
    }
    throw error;
  }

  return share(config, deps, streams);
}

async function share(
  config: Config,
  deps: Dependencies,
  streams: Streams,
): Promise<number> {
  const client = new EvageneClient({
    baseUrl: config.baseUrl,
    apiKey: config.apiKey,
    http: deps.gateway,
  });

  const suffix = config.nameSuffix ?? deps.clock.nowEpochSeconds().toString();
  const keyName = buildKeyName({ pedigreeId: config.pedigreeId, suffix });

  let minted: MintedKey;
  try {
    minted = await client.createReadOnlyApiKey({
      name: keyName,
      ratePerMinute: RATE_PER_MINUTE,
      ratePerDay: RATE_PER_DAY,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_UNAVAILABLE;
    }
    throw error;
  }

  const snippet = buildSnippet({
    embedUrl: client.buildEmbedUrl(config.pedigreeId, minted.plaintextKey),
    label: config.label,
    mintedAt: deps.clock.nowIso(),
    plaintextKey: minted.plaintextKey,
    revokeUrl: `${config.baseUrl.replace(/\/$/, '')}/account/api-keys`,
  });
  present(snippet, streams.stdout);
  return EXIT_OK;
}

function defaultDependencies(): Dependencies {
  return { gateway: new FetchHttpGateway(), clock: new SystemClock() };
}
