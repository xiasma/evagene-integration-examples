import {
  CascadeService,
  NoAtRiskRelativesError,
  type CascadeRequest,
  type CascadeResult,
} from './cascadeService.js';
import { ConfigError, loadConfig, type Config } from './config.js';
import { EvageneApiError, EvageneClient } from './evageneClient.js';
import { FetchHttpGateway, type HttpGateway } from './httpGateway.js';
import { DiskLetterSink } from './letterWriter.js';

export const EXIT_OK = 0;
export const EXIT_USAGE = 64;
export const EXIT_UNAVAILABLE = 69;
export const EXIT_EMPTY = 70;

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
  return runWithGateway(config, new FetchHttpGateway(), streams);
}

async function runWithGateway(
  config: Config,
  gateway: HttpGateway,
  streams: Streams,
): Promise<number> {
  const service = new CascadeService({
    client: new EvageneClient({
      baseUrl: config.baseUrl,
      apiKey: config.apiKey,
      http: gateway,
    }),
    sink: new DiskLetterSink(config.outputDir),
  });
  const request: CascadeRequest =
    config.templateId === undefined
      ? { pedigreeId: config.pedigreeId, dryRun: config.dryRun }
      : {
          pedigreeId: config.pedigreeId,
          dryRun: config.dryRun,
          templateOverride: config.templateId,
        };

  try {
    const result = await service.generateLetters(request);
    report(result, config.dryRun, streams.stdout);
    return EXIT_OK;
  } catch (error) {
    if (error instanceof EvageneApiError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_UNAVAILABLE;
    }
    if (error instanceof NoAtRiskRelativesError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_EMPTY;
    }
    throw error;
  }
}

function report(result: CascadeResult, dryRun: boolean, stdout: TextSink): void {
  if (dryRun) {
    for (const target of result.targets) {
      stdout.write(`${target.displayName} (${target.relationship})\n`);
    }
    return;
  }
  for (const path of result.writtenPaths) {
    stdout.write(`${path}\n`);
  }
}
