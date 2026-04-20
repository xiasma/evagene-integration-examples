/**
 * Thin client for the subset of the Evagene REST API the puzzle generator needs.
 *
 * One method per endpoint, no orchestration.  The orchestrator composes
 * these calls.  The addIndividualToPedigree / designateAsProband methods
 * deliberately tolerate empty response bodies -- Evagene returns an
 * empty body on those endpoints and fetch's .json() throws on empty
 * input.
 */

import type {
  HttpGateway,
  HttpGatewayOptions,
  HttpMethod,
  HttpResponse,
} from './httpGateway.js';
import type { Sex } from './inheritance.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class EvageneApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EvageneApiError';
  }
}

export class DiseaseNotFoundError extends EvageneApiError {
  constructor(message: string) {
    super(message);
    this.name = 'DiseaseNotFoundError';
  }
}

export interface DiseaseSummary {
  readonly diseaseId: string;
  readonly displayName: string;
}

export interface CreateIndividualArgs {
  readonly displayName: string;
  readonly sex: Sex;
}

export interface AddRelativeArgs {
  readonly pedigreeId: string;
  readonly relativeOf: string;
  readonly relativeType: string;
  readonly displayName: string;
  readonly sex: Sex;
}

export interface EvageneApi {
  searchDiseases(nameFragment: string): Promise<DiseaseSummary>;
  createPedigree(displayName: string): Promise<string>;
  createIndividual(args: CreateIndividualArgs): Promise<string>;
  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<void>;
  designateAsProband(individualId: string): Promise<void>;
  addRelative(args: AddRelativeArgs): Promise<string>;
  addDiseaseToIndividual(individualId: string, diseaseId: string): Promise<void>;
  getPedigreeSvg(pedigreeId: string): Promise<string>;
  deletePedigree(pedigreeId: string): Promise<void>;
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

  async searchDiseases(nameFragment: string): Promise<DiseaseSummary> {
    const payload = await this.requestJson('GET', '/api/diseases');
    if (!Array.isArray(payload)) {
      throw new EvageneApiError('Evagene /api/diseases did not return a list.');
    }
    const needle = nameFragment.trim().toLowerCase();
    let exact: DiseaseSummary | null = null;
    let prefix: DiseaseSummary | null = null;
    let substring: DiseaseSummary | null = null;
    for (const raw of payload) {
      if (typeof raw !== 'object' || raw === null) continue;
      const rec = raw as Record<string, unknown>;
      const name = rec.display_name;
      const id = rec.id;
      if (typeof name !== 'string' || typeof id !== 'string') continue;
      const lowered = name.toLowerCase();
      if (lowered === needle && exact === null) {
        exact = { diseaseId: id, displayName: name };
      } else if (lowered.startsWith(needle) && prefix === null) {
        prefix = { diseaseId: id, displayName: name };
      } else if (lowered.includes(needle) && substring === null) {
        substring = { diseaseId: id, displayName: name };
      }
    }
    const match = exact ?? prefix ?? substring;
    if (match === null) {
      throw new DiseaseNotFoundError(
        `No disease in the Evagene catalogue matched ${JSON.stringify(nameFragment)}.`,
      );
    }
    return match;
  }

  async createPedigree(displayName: string): Promise<string> {
    const payload = await this.requestJson('POST', '/api/pedigrees', { display_name: displayName });
    return requireStringField(payload, 'id');
  }

  async createIndividual(args: CreateIndividualArgs): Promise<string> {
    const payload = await this.requestJson('POST', '/api/individuals', {
      display_name: args.displayName,
      biological_sex: args.sex,
    });
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
    const payload = await this.requestJson(
      'POST',
      `/api/pedigrees/${args.pedigreeId}/register/add-relative`,
      {
        relative_of: args.relativeOf,
        relative_type: args.relativeType,
        display_name: args.displayName,
        biological_sex: args.sex,
      },
    );
    const individual = requireObjectField(payload, 'individual');
    return requireStringField(individual, 'id');
  }

  async addDiseaseToIndividual(individualId: string, diseaseId: string): Promise<void> {
    await this.sendIgnoringBody('POST', `/api/individuals/${individualId}/diseases`, {
      disease_id: diseaseId,
    });
  }

  async getPedigreeSvg(pedigreeId: string): Promise<string> {
    const response = await this.dispatch('GET', `/api/pedigrees/${pedigreeId}/export.svg`);
    assert2xx(response, 'GET', `/api/pedigrees/${pedigreeId}/export.svg`);
    return response.text();
  }

  async deletePedigree(pedigreeId: string): Promise<void> {
    await this.sendIgnoringBody('DELETE', `/api/pedigrees/${pedigreeId}`);
  }

  private async requestJson(method: HttpMethod, path: string, body?: unknown): Promise<unknown> {
    const response = await this.dispatch(method, path, body);
    assert2xx(response, method, path);
    try {
      return await response.json();
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      throw new EvageneApiError(
        `Evagene API returned non-JSON body for ${method} ${path}: ${reason}`,
      );
    }
  }

  private async sendIgnoringBody(
    method: HttpMethod,
    path: string,
    body?: unknown,
  ): Promise<void> {
    const response = await this.dispatch(method, path, body);
    assert2xx(response, method, path);
  }

  private async dispatch(
    method: HttpMethod,
    path: string,
    body?: unknown,
  ): Promise<HttpResponse> {
    const options: HttpGatewayOptions = this.buildOptions(method, path, body);
    return this.http.send(options);
  }

  private buildOptions(method: HttpMethod, path: string, body: unknown): HttpGatewayOptions {
    return {
      method,
      url: `${this.baseUrl}${path}`,
      headers: this.headers(),
      ...(body === undefined ? {} : { body }),
    };
  }

  private headers(): Record<string, string> {
    return {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }
}

function assert2xx(response: HttpResponse, method: string, path: string): void {
  if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
    throw new EvageneApiError(
      `Evagene API returned HTTP ${String(response.status)} for ${method} ${path}`,
    );
  }
}

function requireStringField(payload: unknown, key: string): string {
  if (typeof payload !== 'object' || payload === null) {
    throw new EvageneApiError(`Evagene response is not an object, cannot read field '${key}'.`);
  }
  const value = (payload as Record<string, unknown>)[key];
  if (typeof value !== 'string') {
    throw new EvageneApiError(`Evagene response is missing string field '${key}'.`);
  }
  return value;
}

function requireObjectField(payload: unknown, key: string): Record<string, unknown> {
  if (typeof payload !== 'object' || payload === null) {
    throw new EvageneApiError(`Evagene response is not an object, cannot read field '${key}'.`);
  }
  const value = (payload as Record<string, unknown>)[key];
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new EvageneApiError(`Evagene response is missing object field '${key}'.`);
  }
  return value as Record<string, unknown>;
}
