import type { HttpGateway } from './httpGateway.js';

export const CANRISK_HEADER = '##CanRisk 2.0';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export class CanRiskFormatError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CanRiskFormatError';
  }
}

export interface CanRiskClientOptions {
  readonly baseUrl: string;
  readonly apiKey: string;
  readonly http: HttpGateway;
}

export class CanRiskClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly http: HttpGateway;

  constructor(options: CanRiskClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.http = options.http;
  }

  async fetchForPedigree(pedigreeId: string): Promise<string> {
    const url = `${this.baseUrl}/api/pedigrees/${pedigreeId}/risk/canrisk`;
    const response = await this.http.getText(url, { headers: this.headers() });
    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new ApiError(`Evagene API returned HTTP ${response.status.toString()} for ${url}`);
    }

    const body = await response.text();
    if (!body.startsWith(CANRISK_HEADER)) {
      throw new CanRiskFormatError(
        `Response body does not begin with '${CANRISK_HEADER}'; ` +
          `check the pedigree ID and that your key has the 'analyze' scope.`,
      );
    }
    return body;
  }

  private headers(): Record<string, string> {
    return {
      'X-API-Key': this.apiKey,
      Accept: 'text/tab-separated-values',
    };
  }
}
