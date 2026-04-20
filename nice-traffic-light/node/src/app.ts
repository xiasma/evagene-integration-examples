import { ResponseSchemaError, classifyNiceResponse } from './classifier.js';
import { ConfigError, type Config, loadConfig } from './config.js';
import { FetchHttpGateway, type HttpGateway } from './httpGateway.js';
import { type TextSink, present } from './presenter.js';
import { ApiError, RiskApiClient } from './riskApiClient.js';
import { type TrafficLight, toTrafficLight } from './trafficLight.js';

export const EXIT_GREEN = 0;
export const EXIT_AMBER = 1;
export const EXIT_RED = 2;
export const EXIT_USAGE = 64;
export const EXIT_UNAVAILABLE = 69;
export const EXIT_SCHEMA = 70;

export interface Streams {
  readonly stdout: TextSink;
  readonly stderr: TextSink;
}

export async function run(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
  streams: Streams,
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

  return classify(config, new FetchHttpGateway(), streams);
}

async function classify(
  config: Config,
  gateway: HttpGateway,
  streams: Streams,
): Promise<number> {
  const client = new RiskApiClient({
    baseUrl: config.baseUrl,
    apiKey: config.apiKey,
    http: gateway,
  });

  let payload: unknown;
  try {
    payload = await client.calculateNice({
      pedigreeId: config.pedigreeId,
      ...(config.counseleeId !== undefined ? { counseleeId: config.counseleeId } : {}),
    });
  } catch (error) {
    if (error instanceof ApiError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_UNAVAILABLE;
    }
    throw error;
  }

  try {
    const report = toTrafficLight(classifyNiceResponse(payload));
    present(report, streams.stdout);
    return exitCodeFor(report.colour);
  } catch (error) {
    if (error instanceof ResponseSchemaError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_SCHEMA;
    }
    throw error;
  }
}

const EXIT_CODE_BY_COLOUR: Readonly<Record<TrafficLight, number>> = {
  GREEN: EXIT_GREEN,
  AMBER: EXIT_AMBER,
  RED: EXIT_RED,
};

function exitCodeFor(colour: TrafficLight): number {
  return EXIT_CODE_BY_COLOUR[colour];
}
