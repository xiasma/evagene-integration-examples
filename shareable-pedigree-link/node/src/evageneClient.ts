import type { HttpGateway } from './httpGateway.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface MintedKey {
  readonly id: string;
  readonly plaintextKey: string;
}

export interface EvageneClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly http: HttpGateway;
}

export interface CreateApiKeyRequest {
  readonly name: string;
  readonly ratePerMinute: number;
  readonly ratePerDay: number;
}

export class EvageneClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly http: HttpGateway;

  constructor(options: EvageneClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.http = options.http;
  }

  async createReadOnlyApiKey(request: CreateApiKeyRequest): Promise<MintedKey> {
    const url = `${this.baseUrl}/api/auth/me/api-keys`;
    const response = await this.http.postJson(url, {
      headers: this.headers(),
      body: {
        name: request.name,
        scopes: ['read'],
        rate_limit_per_minute: request.ratePerMinute,
        rate_limit_per_day: request.ratePerDay,
      },
    });

    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new ApiError(`Evagene API returned HTTP ${response.status.toString()} for ${url}`);
    }
    return extractMintedKey(await response.json(), url);
  }

  buildEmbedUrl(pedigreeId: string, apiKey: string): string {
    return `${this.baseUrl}/api/embed/${pedigreeId}?api_key=${encodeURIComponent(apiKey)}`;
  }

  private headers(): Record<string, string> {
    return {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }
}

function extractMintedKey(payload: unknown, url: string): MintedKey {
  if (typeof payload !== 'object' || payload === null) {
    throw new ApiError(`Evagene API returned non-object JSON from ${url}`);
  }
  const record = payload as Record<string, unknown>;
  const plaintextKey = record.key;
  const apiKey = record.api_key;
  if (typeof plaintextKey !== 'string' || plaintextKey.length === 0) {
    throw new ApiError(`Evagene API response missing 'key' field from ${url}`);
  }
  if (typeof apiKey !== 'object' || apiKey === null) {
    throw new ApiError(`Evagene API response missing 'api_key' object from ${url}`);
  }
  const id = (apiKey as Record<string, unknown>).id;
  if (typeof id !== 'string' || id.length === 0) {
    throw new ApiError(`Evagene API response missing 'api_key.id' from ${url}`);
  }
  return { id, plaintextKey };
}
