import { ApiError, CanRiskClient, CanRiskFormatError } from './canRiskClient.js';
import { ConfigError, type Config, loadConfig } from './config.js';
import { FetchHttpGateway, type HttpGateway } from './httpGateway.js';
import { OutputSink, PlatformBrowserLauncher } from './outputSink.js';

export const EXIT_OK = 0;
export const EXIT_USAGE = 64;
export const EXIT_UNAVAILABLE = 69;
export const EXIT_FORMAT = 70;

export interface TextSink {
  write(text: string): void;
}

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

  return bridge(config, new FetchHttpGateway(), streams);
}

async function bridge(config: Config, gateway: HttpGateway, streams: Streams): Promise<number> {
  const client = new CanRiskClient({
    baseUrl: config.baseUrl,
    apiKey: config.apiKey,
    http: gateway,
  });

  let payload: string;
  try {
    payload = await client.fetchForPedigree(config.pedigreeId);
  } catch (error) {
    if (error instanceof ApiError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_UNAVAILABLE;
    }
    if (error instanceof CanRiskFormatError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_FORMAT;
    }
    throw error;
  }

  const sink = new OutputSink({
    outputDir: config.outputDir,
    browser: new PlatformBrowserLauncher(),
  });
  const savedPath = sink.save(config.pedigreeId, payload);
  streams.stdout.write(`${savedPath}\n`);

  if (config.openBrowser) {
    sink.openUploadPage();
  }
  return EXIT_OK;
}
