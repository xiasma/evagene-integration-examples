/**
 * Thin client for the subset of the Evagene REST API the bridge uses.
 *
 * One method per endpoint. Orchestration lives in the callers; this
 * class only translates method arguments into HTTP calls and HTTP
 * responses into typed return values.
 */

import type { HttpGateway, HttpMethod } from './httpGateway.js';
import type { BiologicalSex, RelativeType } from './intakeFamily.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class EvageneApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EvageneApiError';
  }
}

export interface EvageneClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly http: HttpGateway;
}

export interface CreatePedigreeArgs {
  readonly displayName: string;
}

export interface CreateIndividualArgs {
  readonly displayName: string;
  readonly biologicalSex: BiologicalSex;
  readonly yearOfBirth?: number;
}

export interface AddRelativeArgs {
  readonly pedigreeId: string;
  readonly relativeOf: string;
  readonly relativeType: RelativeType;
  readonly displayName: string;
  readonly biologicalSex: BiologicalSex;
  readonly yearOfBirth?: number;
}

export interface EvageneApi {
  getPedigreeDetail(pedigreeId: string): Promise<Record<string, unknown>>;
  createPedigree(args: CreatePedigreeArgs): Promise<string>;
  createIndividual(args: CreateIndividualArgs): Promise<string>;
  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<void>;
  designateAsProband(individualId: string): Promise<void>;
  addRelative(args: AddRelativeArgs): Promise<string>;
  deletePedigree(pedigreeId: string): Promise<void>;
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

  async getPedigreeDetail(pedigreeId: string): Promise<Record<string, unknown>> {
    return this.request('GET', `/api/pedigrees/${pedigreeId}`);
  }

  async createPedigree(args: CreatePedigreeArgs): Promise<string> {
    const payload = await this.request('POST', '/api/pedigrees', {
      display_name: args.displayName,
    });
    return requireStringField(payload, 'id');
  }

  async createIndividual(args: CreateIndividualArgs): Promise<string> {
    const body: Record<string, unknown> = {
      display_name: args.displayName,
      biological_sex: args.biologicalSex,
    };
    withYearOfBirth(body, args.yearOfBirth);
    const payload = await this.request('POST', '/api/individuals', body);
    return requireStringField(payload, 'id');
  }

  async addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<void> {
    await this.sendIgnoringBody(
      'POST',
      `/api/pedigrees/${pedigreeId}/individuals/${individualId}`,
      {},
    );
  }

  async designateAsProband(individualId: string): Promise<void> {
    await this.sendIgnoringBody('PATCH', `/api/individuals/${individualId}`, { proband: 1 });
  }

  async addRelative(args: AddRelativeArgs): Promise<string> {
    const body: Record<string, unknown> = {
      relative_of: args.relativeOf,
      relative_type: args.relativeType,
      display_name: args.displayName,
      biological_sex: args.biologicalSex,
    };
    withYearOfBirth(body, args.yearOfBirth);
    const payload = await this.request(
      'POST',
      `/api/pedigrees/${args.pedigreeId}/register/add-relative`,
      body,
    );
    const individual = requireObjectField(payload, 'individual');
    return requireStringField(individual, 'id');
  }

  async deletePedigree(pedigreeId: string): Promise<void> {
    await this.sendIgnoringBody('DELETE', `/api/pedigrees/${pedigreeId}`);
  }

  private async request(
    method: HttpMethod,
    path: string,
    body?: unknown,
  ): Promise<Record<string, unknown>> {
    const response = await this.send(method, path, body);
    return parseObjectBody(response, `${method} ${path}`);
  }

  private async sendIgnoringBody(
    method: HttpMethod,
    path: string,
    body?: unknown,
  ): Promise<void> {
    await this.send(method, path, body);
  }

  private async send(method: HttpMethod, path: string, body: unknown) {
    const url = `${this.baseUrl}${path}`;
    const response = await this.http.send(
      body === undefined
        ? { method, url, headers: this.headers() }
        : { method, url, headers: this.headers(), body },
    );
    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new EvageneApiError(
        `Evagene API returned HTTP ${response.status.toString()} for ${method} ${path}`,
      );
    }
    return response;
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
  response: { json(): Promise<unknown> },
  label: string,
): Promise<Record<string, unknown>> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new EvageneApiError(`Evagene API returned non-JSON body for ${label}: ${reason}`);
  }
  if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
    throw new EvageneApiError(`Evagene API returned non-object JSON for ${label}`);
  }
  return payload as Record<string, unknown>;
}

function withYearOfBirth(body: Record<string, unknown>, year: number | undefined): void {
  if (year === undefined) {
    return;
  }
  body.properties = { year_of_birth: year };
}

function requireStringField(payload: Record<string, unknown>, key: string): string {
  const value = payload[key];
  if (typeof value !== 'string') {
    throw new EvageneApiError(`Evagene response is missing string field '${key}'`);
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
