/**
 * Composition root and runtime entry point.
 */

import type { Readable } from 'node:stream';

import {
  AnthropicExtractor,
  AnthropicGateway,
  type LlmGateway,
  LlmUnavailableError,
} from './anthropicExtractor.js';
import { ConfigError, type Config, loadConfig } from './config.js';
import { EvageneApiError, EvageneClient } from './evageneClient.js';
import { EvageneWriter } from './evageneWriter.js';
import type { ExtractedFamily } from './extractedFamily.js';
import {
  ExtractionSchemaError,
  SYSTEM_PROMPT,
  buildToolSchema,
} from './extractionSchema.js';
import { FetchHttpGateway } from './httpGateway.js';
import { type TextSink, present } from './presenter.js';
import { TranscriptError, readFromPath, readFromStream } from './transcriptSource.js';

export const EXIT_OK = 0;
export const EXIT_USAGE = 64;
export const EXIT_UNAVAILABLE = 69;
export const EXIT_SCHEMA = 70;

export interface Streams {
  readonly stdin: Readable;
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

  if (config.showPrompt) {
    printPrompt(streams.stdout);
    return EXIT_OK;
  }

  let transcript: string;
  try {
    transcript = await readTranscript(config.transcriptPath, streams.stdin);
  } catch (error) {
    if (error instanceof TranscriptError) {
      streams.stderr.write(`error: ${error.message}\n`);
      return EXIT_USAGE;
    }
    throw error;
  }

  const gateway = anthropicGatewayFor(config);
  const extraction = await extract(gateway, transcript, config.model);
  if ('error' in extraction) {
    streams.stderr.write(`error: ${extraction.error.message}\n`);
    return extraction.error.exitCode;
  }

  present(extraction.family, streams.stdout);

  if (!config.commit) {
    return EXIT_OK;
  }
  return commit(extraction.family, config, streams);
}

function readTranscript(path: string | undefined, stdin: Readable): Promise<string> {
  return path !== undefined ? readFromPath(path) : readFromStream(stdin);
}

function printPrompt(stdout: TextSink): void {
  stdout.write('System prompt:\n');
  stdout.write(SYSTEM_PROMPT);
  stdout.write('\n\nTool schema:\n');
  stdout.write(JSON.stringify(buildToolSchema(), null, 2));
  stdout.write('\n');
}

interface ExtractionFailure {
  readonly exitCode: number;
  readonly message: string;
}

type ExtractionResult =
  | { readonly family: ExtractedFamily }
  | { readonly error: ExtractionFailure };

async function extract(
  gateway: LlmGateway,
  transcript: string,
  model: string,
): Promise<ExtractionResult> {
  const extractor = new AnthropicExtractor({ gateway, model });
  try {
    return { family: await extractor.extract(transcript) };
  } catch (error) {
    if (error instanceof LlmUnavailableError) {
      return { error: { exitCode: EXIT_UNAVAILABLE, message: error.message } };
    }
    if (error instanceof ExtractionSchemaError) {
      return { error: { exitCode: EXIT_SCHEMA, message: error.message } };
    }
    throw error;
  }
}

async function commit(
  family: ExtractedFamily,
  config: Config,
  streams: Streams,
): Promise<number> {
  if (config.evageneApiKey === undefined) {
    streams.stderr.write('error: internal: commit invoked without evageneApiKey\n');
    return EXIT_USAGE;
  }
  const client = new EvageneClient({
    baseUrl: config.evageneBaseUrl,
    apiKey: config.evageneApiKey,
    http: new FetchHttpGateway(),
  });
  try {
    const result = await new EvageneWriter(client).write(family);
    streams.stdout.write(`\nCreated pedigree ${result.pedigreeId}\n`);
    streams.stdout.write(
      `${config.evageneBaseUrl.replace(/\/$/, '')}/pedigrees/${result.pedigreeId}\n`,
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

function anthropicGatewayFor(config: Config): LlmGateway {
  if (config.anthropicApiKey === undefined) {
    throw new Error('anthropicApiKey must be set outside --show-prompt mode');
  }
  return new AnthropicGateway(config.anthropicApiKey);
}
