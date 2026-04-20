/**
 * Thin client for the subset of the Evagene REST API the intake form needs.
 *
 * One method per endpoint. No orchestration (that lives in IntakeService).
 * All state goes through the injected HttpGateway so tests can swap in a fake.
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

export type BiologicalSex = 'female' | 'male' | 'unknown';

export type RelativeType =
  | 'mother'
  | 'father'
  | 'maternal_grandmother'
  | 'maternal_grandfather'
  | 'paternal_grandmother'
  | 'paternal_grandfather'
  | 'sister'
  | 'brother'
  | 'half_sister'
  | 'half_brother';

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

/**
 * The subset of the Evagene API that the intake flow depends on.
 * IntakeService talks to this, not the concrete class, so tests
 * supply their own implementation without a live HTTP layer.
 */
export interface EvageneApi {
  createPedigree(args: CreatePedigreeArgs): Promise<string>;
  createIndividual(args: CreateIndividualArgs): Promise<string>;
  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<void>;
  designateAsProband(individualId: string): Promise<void>;
  addRelative(args: AddRelativeArgs): Promise<string>;
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

  async createPedigree(args: CreatePedigreeArgs): Promise<string> {
    const payload = await this.postJson('/api/pedigrees', { display_name: args.displayName });
    return requireStringField(payload, 'id');
  }

  async createIndividual(args: CreateIndividualArgs): Promise<string> {
    const body: Record<string, unknown> = {
      display_name: args.displayName,
      biological_sex: args.biologicalSex,
    };
    withYearOfBirth(body, args.yearOfBirth);
    const payload = await this.postJson('/api/individuals', body);
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
    const payload = await this.postJson(
      `/api/pedigrees/${args.pedigreeId}/register/add-relative`,
      body,
    );
    const individual = requireObjectField(payload, 'individual');
    return requireStringField(individual, 'id');
  }

  private async postJson(path: string, body: unknown): Promise<Record<string, unknown>> {
    const response = await this.send('POST', path, body);
    return parseObjectBody(response, path);
  }

  private async sendIgnoringBody(
    method: 'POST' | 'PATCH',
    path: string,
    body: unknown,
  ): Promise<void> {
    await this.send(method, path, body);
  }

  private async send(method: 'POST' | 'PATCH', path: string, body: unknown) {
    const url = `${this.baseUrl}${path}`;
    const response = await this.http.send({
      method,
      url,
      headers: this.headers(),
      body,
    });
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
  path: string,
): Promise<Record<string, unknown>> {
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
