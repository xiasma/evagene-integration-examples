/**
 * Immutable CLI + environment configuration.
 */

import { type Mode, MODES } from './inheritance.js';
import type { Generations, Size } from './puzzleBlueprint.js';

const DEFAULT_BASE_URL = 'https://evagene.net';
const DEFAULT_OUTPUT_DIR = './puzzles';

const DEFAULT_DISEASE_BY_MODE: Readonly<Record<Mode, string>> = {
  AD: "Huntington's Disease",
  AR: 'Cystic Fibrosis',
  XLR: 'Haemophilia A',
  XLD: 'Rett Syndrome',
  MT: 'Leber Hereditary Optic Neuropathy',
};

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

export interface Config {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly mode: Mode | null;
  readonly generations: Generations;
  readonly size: Size;
  readonly diseaseName: string | null;
  readonly outputDir: string;
  readonly cleanup: boolean;
  readonly seed: number;
}

export function defaultDiseaseFor(mode: Mode): string {
  return DEFAULT_DISEASE_BY_MODE[mode];
}

export function loadConfig(
  argv: readonly string[],
  env: Readonly<Record<string, string | undefined>>,
): Config {
  const args = parseArgs(argv);

  const apiKey = (env.EVAGENE_API_KEY ?? '').trim();
  if (!apiKey) {
    throw new ConfigError('EVAGENE_API_KEY environment variable is required.');
  }
  const baseUrl = (env.EVAGENE_BASE_URL ?? '').trim() || DEFAULT_BASE_URL;

  return {
    baseUrl,
    apiKey,
    mode: parseMode(args.mode),
    generations: parseGenerations(args.generations),
    size: parseSize(args.size),
    diseaseName: parseDiseaseName(args.disease),
    outputDir: args.outputDir,
    cleanup: !args.noCleanup,
    seed: args.seed ?? randomSeed(),
  };
}

interface RawArgs {
  mode: string;
  generations: string;
  size: string;
  disease: string | null;
  outputDir: string;
  noCleanup: boolean;
  seed: number | null;
}

function parseArgs(argv: readonly string[]): RawArgs {
  const out: RawArgs = {
    mode: 'random',
    generations: '3',
    size: 'medium',
    disease: null,
    outputDir: DEFAULT_OUTPUT_DIR,
    noCleanup: false,
    seed: null,
  };
  let index = 0;
  while (index < argv.length) {
    const token = argv[index] ?? '';
    const value = argv[index + 1];
    switch (token) {
      case '--mode':
        out.mode = requireValue(token, value);
        index += 2;
        break;
      case '--generations':
        out.generations = requireValue(token, value);
        index += 2;
        break;
      case '--size':
        out.size = requireValue(token, value);
        index += 2;
        break;
      case '--disease':
        out.disease = requireValue(token, value);
        index += 2;
        break;
      case '--output-dir':
        out.outputDir = requireValue(token, value);
        index += 2;
        break;
      case '--no-cleanup':
        out.noCleanup = true;
        index += 1;
        break;
      case '--seed':
        out.seed = parseInteger(token, requireValue(token, value));
        index += 2;
        break;
      default:
        throw new ConfigError(`Unexpected argument: ${token}`);
    }
  }
  return out;
}

function requireValue(flag: string, value: string | undefined): string {
  if (value === undefined) {
    throw new ConfigError(`${flag} requires a value`);
  }
  return value;
}

function parseInteger(flag: string, raw: string): number {
  const trimmed = raw.trim();
  if (!/^-?\d+$/.test(trimmed)) {
    throw new ConfigError(`${flag} must be an integer; got ${JSON.stringify(raw)}`);
  }
  return Number.parseInt(trimmed, 10);
}

function parseMode(raw: string): Mode | null {
  const normalised = raw.trim().toUpperCase();
  if (normalised === 'RANDOM') return null;
  const match = MODES.find((mode) => mode === normalised);
  if (match === undefined) {
    throw new ConfigError(
      `--mode must be one of ${MODES.join(', ')} or 'random'; got ${JSON.stringify(raw)}`,
    );
  }
  return match;
}

function parseGenerations(raw: string): Generations {
  const value = parseInteger('--generations', raw);
  if (value !== 3 && value !== 4) {
    throw new ConfigError(`--generations must be 3 or 4; got ${String(value)}`);
  }
  return value;
}

function parseSize(raw: string): Size {
  const normalised = raw.trim().toLowerCase();
  if (normalised !== 'small' && normalised !== 'medium' && normalised !== 'large') {
    throw new ConfigError(
      `--size must be one of small, medium, large; got ${JSON.stringify(raw)}`,
    );
  }
  return normalised;
}

function parseDiseaseName(raw: string | null): string | null {
  if (raw === null) return null;
  const trimmed = raw.trim();
  if (trimmed === '') {
    throw new ConfigError('--disease must not be empty.');
  }
  return trimmed;
}

function randomSeed(): number {
  // 31 bits keeps the value within the safe integer range and the
  // PRNG's 32-bit state.
  return Math.floor(Math.random() * 0x7fffffff);
}
