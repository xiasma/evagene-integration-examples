/**
 * Thin client for the Evagene REST endpoints the dashboard needs.
 *
 * One method per endpoint.  All I/O goes through the injected HttpGateway
 * so tests can replace it with a fake.  Errors carry enough context for
 * the caller to decide whether to render a degraded card or abort.
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

export interface PedigreeSummary {
  readonly id: string;
  readonly displayName: string;
}

export interface EvageneClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly http: HttpGateway;
}

export interface EvageneApi {
  fetchEmbedSvg(pedigreeId: string): Promise<string>;
  calculateNice(pedigreeId: string): Promise<unknown>;
  getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary>;
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

  async fetchEmbedSvg(pedigreeId: string): Promise<string> {
    const path = `/api/embed/${pedigreeId}/svg`;
    const response = await this.http.getText(this.urlFor(path), this.authHeaders());
    ensureOk(response.status, 'GET', path);
    return response.text();
  }

  async calculateNice(pedigreeId: string): Promise<unknown> {
    const path = `/api/pedigrees/${pedigreeId}/risk/calculate`;
    const response = await this.http.postJson(
      this.urlFor(path),
      this.authHeaders({ 'Content-Type': 'application/json', Accept: 'application/json' }),
      { model: 'NICE' },
    );
    ensureOk(response.status, 'POST', path);
    return response.json();
  }

  async getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary> {
    const path = `/api/pedigrees/${pedigreeId}`;
    const response = await this.http.getText(
      this.urlFor(path),
      this.authHeaders({ Accept: 'application/json' }),
    );
    ensureOk(response.status, 'GET', path);
    const parsed = parseJsonObject(await response.text(), path);
    return {
      id: readString(parsed, 'id', path),
      displayName: readString(parsed, 'display_name', path),
    };
  }

  private urlFor(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  private authHeaders(extra: Readonly<Record<string, string>> = {}): Record<string, string> {
    return { 'X-API-Key': this.apiKey, ...extra };
  }
}

function ensureOk(status: number, method: string, path: string): void {
  if (status < HTTP_OK_LOWER || status >= HTTP_OK_UPPER) {
    throw new EvageneApiError(
      `Evagene API returned HTTP ${status.toString()} for ${method} ${path}`,
    );
  }
}

function parseJsonObject(text: string, path: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new EvageneApiError(`Evagene API returned non-JSON body for ${path}: ${reason}`);
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new EvageneApiError(`Evagene API returned non-object JSON for ${path}`);
  }
  return parsed as Record<string, unknown>;
}

function readString(container: Record<string, unknown>, key: string, path: string): string {
  const value = container[key];
  if (typeof value !== 'string') {
    throw new EvageneApiError(`Evagene API response for ${path} is missing string field '${key}'`);
  }
  return value;
}
