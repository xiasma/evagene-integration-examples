/**
 * Minimal FHIR R5 client for the two calls the bridge makes:
 *   GET  [base]/FamilyMemberHistory?patient={id}  -> searchset Bundle
 *   POST [base]                                   -> transaction Bundle
 *
 * One class, two methods. No FHIR SDK dependency, so the reader can
 * see the literal HTTP at play.
 */

import type { FhirBundle } from './fhirTypes.js';
import type { HttpGateway, HttpRequest } from './httpGateway.js';

const HTTP_OK_LOWER = 200;
const HTTP_OK_UPPER = 300;
const FHIR_CONTENT_TYPE = 'application/fhir+json';

export class FhirApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'FhirApiError';
  }
}

export interface FhirClientOptions {
  readonly baseUrl: string;
  readonly http: HttpGateway;
  readonly authHeader?: string;
}

export class FhirClient {
  private readonly baseUrl: string;
  private readonly http: HttpGateway;
  private readonly authHeader?: string;

  constructor(options: FhirClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.http = options.http;
    if (options.authHeader !== undefined) {
      this.authHeader = options.authHeader;
    }
  }

  async fetchFamilyHistoryForPatient(patientId: string): Promise<FhirBundle> {
    const url = `${this.baseUrl}/FamilyMemberHistory?patient=${encodeURIComponent(patientId)}`;
    const payload = await this.sendExpectingBundle({
      method: 'GET',
      url,
      headers: this.headers(),
    });
    if (payload.type !== 'searchset' && payload.type !== 'collection') {
      throw new FhirApiError(
        `FHIR server returned Bundle of unexpected type '${payload.type}'; expected 'searchset'.`,
      );
    }
    return payload;
  }

  async postTransactionBundle(bundle: FhirBundle): Promise<FhirBundle> {
    if (bundle.type !== 'transaction') {
      throw new FhirApiError(`postTransactionBundle requires a Bundle of type 'transaction'.`);
    }
    return this.sendExpectingBundle({
      method: 'POST',
      url: this.baseUrl,
      headers: this.headers(),
      body: bundle,
    });
  }

  private async sendExpectingBundle(request: HttpRequest): Promise<FhirBundle> {
    const response = await this.http.send(request);
    if (response.status < HTTP_OK_LOWER || response.status >= HTTP_OK_UPPER) {
      throw new FhirApiError(
        `FHIR server returned HTTP ${response.status.toString()} for ${request.method} ${request.url}`,
      );
    }
    let payload: unknown;
    try {
      payload = await response.json();
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      throw new FhirApiError(`FHIR server returned non-JSON body: ${reason}`);
    }
    if (
      typeof payload !== 'object' ||
      payload === null ||
      (payload as { resourceType?: unknown }).resourceType !== 'Bundle'
    ) {
      throw new FhirApiError('FHIR server returned a resource that is not a Bundle.');
    }
    return payload as FhirBundle;
  }

  private headers(): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: FHIR_CONTENT_TYPE,
      'Content-Type': FHIR_CONTENT_TYPE,
    };
    if (this.authHeader !== undefined) {
      const [name, ...rest] = this.authHeader.split(':');
      if (name !== undefined && rest.length > 0) {
        headers[name.trim()] = rest.join(':').trim();
      }
    }
    return headers;
  }
}
