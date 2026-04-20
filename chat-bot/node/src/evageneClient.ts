/**
 * Subset of the Evagene REST API the chat-bot needs.
 *
 *   GET  /api/pedigrees/{id}/summary          -> pedigree name + proband name
 *   GET  /api/pedigrees/{id}/export.svg       -> (URL only; Slack/Teams link to it)
 *   POST /api/pedigrees/{id}/risk/calculate   -> NICE category + triggers
 */

import type { HttpGateway } from './httpGateway.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class EvageneApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EvageneApiError';
  }
}

export type NiceCategory = 'GREEN' | 'AMBER' | 'RED';

export interface PedigreeSummary {
  readonly pedigreeId: string;
  readonly displayName: string;
  readonly probandName: string | undefined;
}

export interface NiceResult {
  readonly category: NiceCategory;
  readonly triggers: readonly string[];
  readonly referForGeneticsAssessment: boolean;
}

export interface EvageneApi {
  getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary>;
  svgUrlFor(pedigreeId: string): string;
  pedigreeWebUrlFor(pedigreeId: string): string;
  calculateNice(pedigreeId: string): Promise<NiceResult>;
}

export interface EvageneClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly http: HttpGateway;
}

export class EvageneClient implements EvageneApi {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly http: HttpGateway;

  constructor(options: EvageneClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.http = options.http;
  }

  async getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary> {
    const path = `/api/pedigrees/${pedigreeId}/summary`;
    const payload = await this.getJson(path);
    return {
      pedigreeId,
      displayName: requireStringField(payload, 'name'),
      probandName: readProbandName(payload),
    };
  }

  svgUrlFor(pedigreeId: string): string {
    return `${this.baseUrl}/api/pedigrees/${pedigreeId}/export.svg`;
  }

  pedigreeWebUrlFor(pedigreeId: string): string {
    return `${this.baseUrl}/pedigrees/${pedigreeId}`;
  }

  async calculateNice(pedigreeId: string): Promise<NiceResult> {
    const path = `/api/pedigrees/${pedigreeId}/risk/calculate`;
    const response = await this.http.send({
      method: 'POST',
      url: `${this.baseUrl}${path}`,
      headers: this.headers(),
      body: { model: 'NICE' },
    });
    return parseNiceResult(await parseObjectBody(response, path));
  }

  private async getJson(path: string): Promise<Record<string, unknown>> {
    const response = await this.http.send({
      method: 'GET',
      url: `${this.baseUrl}${path}`,
      headers: this.headers(),
    });
    return parseObjectBody(response, path);
  }

  private headers(): Record<string, string> {
    return {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }
}

async function parseObjectBody(
  response: { readonly status: number; json(): Promise<unknown> },
  path: string,
): Promise<Record<string, unknown>> {
  if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
    throw new EvageneApiError(
      `Evagene API returned HTTP ${response.status.toString()} for ${path}`,
    );
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new EvageneApiError(`Evagene API returned non-JSON body for ${path}: ${reason}`);
  }
  if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
    throw new EvageneApiError(`Evagene API returned non-object JSON for ${path}`);
  }
  return payload as Record<string, unknown>;
}

function parseNiceResult(payload: Record<string, unknown>): NiceResult {
  const cancerRisk = requireObjectField(payload, 'cancer_risk');
  return {
    category: parseCategory(requireStringField(cancerRisk, 'nice_category')),
    triggers: readStringList(cancerRisk, 'nice_triggers'),
    referForGeneticsAssessment: requireBooleanField(cancerRisk, 'nice_refer_genetics'),
  };
}

const CATEGORY_BY_NAME: Readonly<Record<string, NiceCategory>> = {
  near_population: 'GREEN',
  moderate: 'AMBER',
  high: 'RED',
};

function parseCategory(raw: string): NiceCategory {
  const mapped = CATEGORY_BY_NAME[raw];
  if (mapped === undefined) {
    throw new EvageneApiError(`Unknown NICE category: ${JSON.stringify(raw)}`);
  }
  return mapped;
}

function readProbandName(payload: Record<string, unknown>): string | undefined {
  const proband = payload.proband;
  if (typeof proband !== 'object' || proband === null || Array.isArray(proband)) {
    return undefined;
  }
  const name = (proband as Record<string, unknown>).name;
  return typeof name === 'string' && name !== '' ? name : undefined;
}

function requireStringField(payload: Record<string, unknown>, key: string): string {
  const value = payload[key];
  if (typeof value !== 'string') {
    throw new EvageneApiError(`Evagene response is missing string field '${key}'`);
  }
  return value;
}

function requireBooleanField(payload: Record<string, unknown>, key: string): boolean {
  const value = payload[key];
  if (typeof value !== 'boolean') {
    throw new EvageneApiError(`Evagene response is missing boolean field '${key}'`);
  }
  return value;
}

function requireObjectField(
  payload: Record<string, unknown>,
  key: string,
): Record<string, unknown> {
  const value = payload[key];
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new EvageneApiError(`Evagene response is missing object field '${key}'`);
  }
  return value as Record<string, unknown>;
}

function readStringList(
  payload: Record<string, unknown>,
  key: string,
): readonly string[] {
  const value = payload[key];
  if (value === undefined) {
    return [];
  }
  if (!Array.isArray(value) || !value.every(item => typeof item === 'string')) {
    throw new EvageneApiError(`Evagene response field '${key}' is not a list of strings`);
  }
  return value;
}
