/**
 * Thin adapter over the built-in `fetch`.
 *
 * The gateway is a seam: tests pass a fake, production uses FetchHttpGateway.
 */

export interface HttpResponse {
  readonly status: number;
  json(): Promise<unknown>;
}

export interface HttpRequest {
  readonly method: 'GET' | 'POST';
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body?: unknown;
}

export interface HttpGateway {
  send(request: HttpRequest): Promise<HttpResponse>;
}

export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 10_000) {}

  async send(request: HttpRequest): Promise<HttpResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => { controller.abort(); }, this.timeoutMs);
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
        json: () => response.json() as Promise<unknown>,
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
