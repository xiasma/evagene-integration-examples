import type { HttpGateway, HttpResponse } from './httpGateway.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export type JsonObject = Record<string, unknown>;

export interface EvageneClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly http: HttpGateway;
}

export interface CalculateRiskArgs {
  readonly pedigreeId: string;
  readonly model: string;
  readonly counseleeId?: string;
}

export interface CreateIndividualArgs {
  readonly displayName: string;
  readonly biologicalSex: string;
}

export interface AddRelativeArgs {
  readonly pedigreeId: string;
  readonly relativeOf: string;
  readonly relativeType: string;
  readonly displayName?: string;
  readonly biologicalSex?: string;
}

/** Thin, typed wrapper over the Evagene REST endpoints the MCP tools need. */
export class EvageneClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly http: HttpGateway;

  constructor(options: EvageneClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.http = options.http;
  }

  async listPedigrees(): Promise<JsonObject[]> {
    const payload = await this.getJson('/api/pedigrees');
    if (!Array.isArray(payload)) {
      throw new ApiError(`Expected a JSON array from /api/pedigrees, got ${typeOf(payload)}`);
    }
    return payload as JsonObject[];
  }

  getPedigree(pedigreeId: string): Promise<JsonObject> {
    return this.getObject(`/api/pedigrees/${pedigreeId}`);
  }

  describePedigree(pedigreeId: string): Promise<string> {
    return this.getText(`/api/pedigrees/${pedigreeId}/describe`);
  }

  listRiskModels(pedigreeId: string): Promise<JsonObject> {
    return this.getObject(`/api/pedigrees/${pedigreeId}/risk/models`);
  }

  calculateRisk(args: CalculateRiskArgs): Promise<JsonObject> {
    const body: JsonObject = { model: args.model };
    if (args.counseleeId !== undefined) {
      body.counselee_id = args.counseleeId;
    }
    return this.postObject(`/api/pedigrees/${args.pedigreeId}/risk/calculate`, body);
  }

  createIndividual(args: CreateIndividualArgs): Promise<JsonObject> {
    return this.postObject('/api/individuals', {
      display_name: args.displayName,
      biological_sex: args.biologicalSex,
    });
  }

  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<JsonObject> {
    return this.postObject(
      `/api/pedigrees/${pedigreeId}/individuals/${individualId}`,
      {},
    );
  }

  addRelative(args: AddRelativeArgs): Promise<JsonObject> {
    const body: JsonObject = {
      relative_of: args.relativeOf,
      relative_type: args.relativeType,
      display_name: args.displayName ?? '',
    };
    if (args.biologicalSex !== undefined) {
      body.biological_sex = args.biologicalSex;
    }
    return this.postObject(`/api/pedigrees/${args.pedigreeId}/register/add-relative`, body);
  }

  // ------------------------------------------------------------------
  // Transport helpers
  // ------------------------------------------------------------------

  private async getJson(path: string): Promise<unknown> {
    const response = await this.http.request(this.url(path), {
      method: 'GET',
      headers: this.headers(),
    });
    this.raiseForStatus(response, path);
    return response.json();
  }

  private async getObject(path: string): Promise<JsonObject> {
    return requireObject(await this.getJson(path), path);
  }

  private async getText(path: string): Promise<string> {
    const response = await this.http.request(this.url(path), {
      method: 'GET',
      headers: this.headers(),
    });
    this.raiseForStatus(response, path);
    return response.text();
  }

  private async postObject(path: string, body: JsonObject): Promise<JsonObject> {
    const response = await this.http.request(this.url(path), {
      method: 'POST',
      headers: this.headers(),
      body,
    });
    this.raiseForStatus(response, path);
    return requireObject(await response.json(), path);
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  private headers(): Record<string, string> {
    return {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  private raiseForStatus(response: HttpResponse, path: string): void {
    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new ApiError(`Evagene API returned HTTP ${response.status.toString()} for ${path}`);
    }
  }
}

function requireObject(value: unknown, path: string): JsonObject {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new ApiError(`Expected JSON object from ${path}, got ${typeOf(value)}`);
  }
  return value as JsonObject;
}

function typeOf(value: unknown): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  return typeof value;
}
