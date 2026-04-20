/**
 * Transport-layer abstraction shared by the Evagene and FHIR clients.
 *
 * A single `send` operation keeps the client code free of branching on
 * verb, and lets the tests supply a recording fake without stubbing
 * four methods where one will do.
 */

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE';

export interface HttpRequest {
  readonly method: HttpMethod;
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body?: unknown;
}

export interface HttpResponse {
  readonly status: number;
  text(): Promise<string>;
  json(): Promise<unknown>;
}

export interface HttpGateway {
  send(request: HttpRequest): Promise<HttpResponse>;
}

/** Thin adapter over the built-in `fetch`. */
export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 15_000) {}

  async send(request: HttpRequest): Promise<HttpResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);
    try {
      const init: RequestInit = {
        method: request.method,
        headers: request.headers,
        signal: controller.signal,
      };
      if (request.body !== undefined) {
        init.body = JSON.stringify(request.body);
      }
      const response = await fetch(request.url, init);
      return {
        status: response.status,
        text: () => response.text(),
        json: () => response.json() as Promise<unknown>,
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
