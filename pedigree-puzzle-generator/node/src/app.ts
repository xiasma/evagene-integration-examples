/**
 * Composition root and CLI runner.
 */

import { ConfigError, type Config, defaultDiseaseFor, loadConfig } from './config.js';
import {
  EvageneApiError,
  EvageneClient,
  type EvageneApi,
} from './evageneClient.js';
import { FetchHttpGateway, type HttpGateway } from './httpGateway.js';
import { MODES, type Mode } from './inheritance.js';
import { type Clock, type Logger, PuzzleOrchestrator } from './orchestrator.js';
import { buildBlueprint } from './puzzleBlueprint.js';
import { createRng } from './random.js';

export const EXIT_OK = 0;
export const EXIT_USAGE = 64;
export const EXIT_UNAVAILABLE = 69;
export const EXIT_SOFTWARE = 70;

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

  const gateway = new FetchHttpGateway();
  return generate(config, gateway, streams);
}

async function generate(
  config: Config,
  gateway: HttpGateway,
  streams: Streams,
): Promise<number> {
  const chosenMode: Mode = config.mode ?? randomMode(config.seed);
  const diseaseName = config.diseaseName ?? defaultDiseaseFor(chosenMode);
  const blueprint = buildBlueprint({
    mode: chosenMode,
    generations: config.generations,
    size: config.size,
    seed: config.seed,
  });

  const client: EvageneApi = new EvageneClient({
    baseUrl: config.baseUrl,
    apiKey: config.apiKey,
    http: gateway,
  });

  const orchestrator = new PuzzleOrchestrator({
    client,
    clock: systemClock(),
    evageneBaseUrl: config.baseUrl,
    logger: stderrLogger(streams.stderr),
  });

  try {
    const result = await orchestrator.generate({
      blueprint,
      diseaseName,
      outputDir: config.outputDir,
      cleanup: config.cleanup,
    });
    streams.stdout.write(`Wrote ${result.artefact.questionPath}\n`);
    streams.stdout.write(`Wrote ${result.artefact.answerPath}\n`);
    streams.stdout.write(
      `Pedigree on Evagene: ${config.baseUrl}/pedigrees/${result.pedigreeId}` +
        (result.pedigreeWasDeleted ? ' (deleted)' : '') +
        '\n',
    );
    return EXIT_OK;
  } catch (error) {
    if (error instanceof EvageneApiError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_UNAVAILABLE;
    }
    throw error;
  }
}

function randomMode(seed: number): Mode {
  const rng = createRng(seed ^ 0xa5a5);
  return rng.choice(MODES);
}

function systemClock(): Clock {
  return {
    now(): Date {
      return new Date();
    },
  };
}

function stderrLogger(stderr: TextSink): Logger {
  return {
    info(message) {
      stderr.write(`INFO ${message}\n`);
    },
    warn(message) {
      stderr.write(`WARNING ${message}\n`);
    },
  };
}
