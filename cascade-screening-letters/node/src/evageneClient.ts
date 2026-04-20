/**
 * Thin client for the Evagene endpoints used by the cascade-letters demo.
 * One method per endpoint; parses response JSON into small domain types.
 */

import type { HttpGateway, HttpMethod } from './httpGateway.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class EvageneApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EvageneApiError';
  }
}

export interface RegisterRow {
  readonly individualId: string;
  readonly displayName: string;
  readonly relationshipToProband: string;
}

export interface RegisterData {
  readonly probandId: string | null;
  readonly rows: readonly RegisterRow[];
}

export interface Template {
  readonly id: string;
  readonly name: string;
}

export interface CreateTemplateArgs {
  readonly name: string;
  readonly description: string;
  readonly userPromptTemplate: string;
}

export interface EvageneApi {
  fetchRegister(pedigreeId: string): Promise<RegisterData>;
  listTemplates(): Promise<readonly Template[]>;
  createTemplate(args: CreateTemplateArgs): Promise<Template>;
  runTemplate(templateId: string, pedigreeId: string): Promise<string>;
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

  async fetchRegister(pedigreeId: string): Promise<RegisterData> {
    const payload = await this.request('GET', `/api/pedigrees/${pedigreeId}/register`);
    const root = requireObject(payload, 'register response');
    const rowsRaw = root.rows;
    if (!Array.isArray(rowsRaw)) {
      throw new EvageneApiError("Register response field 'rows' is not an array.");
    }
    return {
      probandId: typeof root.proband_id === 'string' ? root.proband_id : null,
      rows: rowsRaw.map(parseRegisterRow),
    };
  }

  async listTemplates(): Promise<readonly Template[]> {
    const payload = await this.request('GET', '/api/templates');
    if (!Array.isArray(payload)) {
      throw new EvageneApiError('GET /api/templates did not return a JSON array.');
    }
    return payload.map(parseTemplate);
  }

  async createTemplate(args: CreateTemplateArgs): Promise<Template> {
    const body = {
      name: args.name,
      description: args.description,
      user_prompt_template: args.userPromptTemplate,
      is_public: false,
    };
    const payload = await this.request('POST', '/api/templates', body);
    return parseTemplate(payload);
  }

  async runTemplate(templateId: string, pedigreeId: string): Promise<string> {
    // Server takes pedigree_id as a query parameter; no request body is accepted.
    const path = `/api/templates/${templateId}/run?pedigree_id=${pedigreeId}`;
    const payload = await this.request('POST', path, {});
    const root = requireObject(payload, 'template run response');
    const text = root.text;
    if (typeof text !== 'string') {
      throw new EvageneApiError("Template run response is missing string field 'text'.");
    }
    return text;
  }

  private async request(method: HttpMethod, path: string, body?: unknown): Promise<unknown> {
    const url = `${this.baseUrl}${path}`;
    const options = body === undefined ? { headers: this.headers() } : { headers: this.headers(), body };
    const response = await this.http.send(method, url, options);
    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new EvageneApiError(
        `Evagene API returned HTTP ${response.status.toString()} for ${method} ${path}`,
      );
    }
    return response.json();
  }

  private headers(): Record<string, string> {
    return {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }
}

function parseRegisterRow(raw: unknown): RegisterRow {
  const row = requireObject(raw, 'register row');
  return {
    individualId: requireString(row, 'individual_id'),
    displayName: optionalString(row, 'display_name'),
    relationshipToProband: optionalString(row, 'relationship_to_proband'),
  };
}

function parseTemplate(raw: unknown): Template {
  const obj = requireObject(raw, 'template');
  return {
    id: requireString(obj, 'id'),
    name: optionalString(obj, 'name'),
  };
}

function requireObject(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new EvageneApiError(`${label} is not a JSON object`);
  }
  return value as Record<string, unknown>;
}

function requireString(container: Record<string, unknown>, key: string): string {
  const value = container[key];
  if (typeof value !== 'string') {
    throw new EvageneApiError(`Response field '${key}' is missing or not a string.`);
  }
  return value;
}

function optionalString(container: Record<string, unknown>, key: string): string {
  const value = container[key];
  return typeof value === 'string' ? value : '';
}
