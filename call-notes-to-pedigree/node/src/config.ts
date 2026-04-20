/**
 * Immutable configuration for the call-notes-to-pedigree CLI.
 */

import { DEFAULT_MODEL } from './anthropicExtractor.js';

const DEFAULT_BASE_URL = 'https://evagene.net';

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export interface Config {
  readonly transcriptPath: string | undefined;
  readonly commit: boolean;
  readonly showPrompt: boolean;
  readonly model: string;
  readonly anthropicApiKey: string | undefined;
  readonly evageneApiKey: string | undefined;
  readonly evageneBaseUrl: string;
}

export { DEFAULT_BASE_URL };

export function loadConfig(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
): Config {
  const args = parseArgs(argv);
  const model = args.model ?? DEFAULT_MODEL;
  const evageneBaseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;

  if (args.showPrompt) {
    return {
      transcriptPath: args.transcriptPath,
      commit: false,
      showPrompt: true,
      model,
      anthropicApiKey: undefined,
      evageneApiKey: undefined,
      evageneBaseUrl,
    };
  }

  const anthropicApiKey = (env.ANTHROPIC_API_KEY ?? '').trim();
  if (anthropicApiKey === '') {
    throw new ConfigError('ANTHROPIC_API_KEY environment variable is required.');
  }

  let evageneApiKey: string | undefined;
  if (args.commit) {
    const key = (env.EVAGENE_API_KEY ?? '').trim();
    if (key === '') {
      throw new ConfigError(
        '--commit requires the EVAGENE_API_KEY environment variable to be set.',
      );
    }
    evageneApiKey = key;
  }

  return {
    transcriptPath: args.transcriptPath,
    commit: args.commit,
    showPrompt: false,
    model,
    anthropicApiKey,
    evageneApiKey,
    evageneBaseUrl,
  };
}

interface ParsedArgs {
  readonly transcriptPath: string | undefined;
  readonly commit: boolean;
  readonly showPrompt: boolean;
  readonly model: string | undefined;
}

function parseArgs(argv: readonly string[]): ParsedArgs {
  let transcriptPath: string | undefined;
  let commit = false;
  let showPrompt = false;
  let model: string | undefined;

  let index = 0;
  while (index < argv.length) {
    const token = argv[index] ?? '';
    if (token === '--commit') {
      commit = true;
      index += 1;
    } else if (token === '--show-prompt') {
      showPrompt = true;
      index += 1;
    } else if (token === '--model') {
      const value = argv[index + 1];
      if (value === undefined) {
        throw new ConfigError('--model requires a value');
      }
      model = value;
      index += 2;
    } else if (!token.startsWith('--') && transcriptPath === undefined) {
      transcriptPath = token;
      index += 1;
    } else {
      throw new ConfigError(`Unexpected argument: ${token}`);
    }
  }

  return { transcriptPath, commit, showPrompt, model };
}
