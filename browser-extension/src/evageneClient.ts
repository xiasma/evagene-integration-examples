/**
 * Minimal Evagene REST client used by the background service worker.
 *
 * Owns no state other than its constructor arguments. The caller supplies
 * a fetch implementation so the tests can stand in a fake one without
 * touching global state.
 */

import type { PedigreeSummary } from './messaging.js';

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface EvageneClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly fetch: FetchLike;
}

export class EvageneError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EvageneError';
  }
}

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class EvageneClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly fetchFn: FetchLike;

  constructor(options: EvageneClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.fetchFn = options.fetch;
  }

  async getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary> {
    const url = `${this.baseUrl}/api/pedigrees/${pedigreeId}/summary`;
    const response = await this.fetchFn(url, { headers: this.headers() });
    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new EvageneError(
        `Evagene API returned HTTP ${response.status.toString()} for ${url}`,
      );
    }
    const payload: unknown = await response.json();
    return toSummary(payload, `${this.baseUrl}/pedigrees/${pedigreeId}`);
  }

  private headers(): Record<string, string> {
    return { 'X-API-Key': this.apiKey, Accept: 'application/json' };
  }
}

function toSummary(payload: unknown, viewUrl: string): PedigreeSummary {
  const root = asObject(payload, 'response');
  return {
    pedigreeId: requireString(root, 'pedigree_id'),
    name: requireString(root, 'name'),
    probandName: readProbandName(root.proband),
    diseases: Object.keys(asObject(root.diseases_in_family, 'diseases_in_family')),
    viewUrl,
  };
}

function readProbandName(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const proband = asObject(value, 'proband');
  const name = proband.name;
  return typeof name === 'string' ? name : null;
}

function asObject(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new EvageneError(`${label} is not an object in API response`);
  }
  return value as Record<string, unknown>;
}

function requireString(container: Record<string, unknown>, key: string): string {
  const value = container[key];
  if (typeof value !== 'string') {
    throw new EvageneError(`field '${key}' is missing or not a string`);
  }
  return value;
}
