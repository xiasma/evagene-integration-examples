import type { HttpGateway } from './httpGateway.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface RiskApiClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly http: HttpGateway;
}

export interface CalculateNiceArgs {
  readonly pedigreeId: string;
  readonly counseleeId?: string;
}

export class RiskApiClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly http: HttpGateway;

  constructor(options: RiskApiClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.http = options.http;
  }

  async calculateNice(args: CalculateNiceArgs): Promise<unknown> {
    const url = `${this.baseUrl}/api/pedigrees/${args.pedigreeId}/risk/calculate`;
    const body: Record<string, unknown> = { model: 'NICE' };
    if (args.counseleeId !== undefined) {
      body.counselee_id = args.counseleeId;
    }

    const response = await this.http.postJson(url, { headers: this.headers(), body });
    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new ApiError(`Evagene API returned HTTP ${response.status.toString()} for ${url}`);
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
