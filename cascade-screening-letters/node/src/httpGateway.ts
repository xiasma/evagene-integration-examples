export type HttpMethod = 'GET' | 'POST';

export interface HttpResponse {
  readonly status: number;
  json(): Promise<unknown>;
}

export interface HttpGatewayOptions {
  readonly headers: Record<string, string>;
  readonly body?: unknown;
}

export interface HttpGateway {
  send(method: HttpMethod, url: string, options: HttpGatewayOptions): Promise<HttpResponse>;
}

/** Thin adapter over the built-in `fetch`. */
export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 30_000) {}

  async send(
    method: HttpMethod,
    url: string,
    options: HttpGatewayOptions,
  ): Promise<HttpResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);
    try {
      const init: RequestInit = {
        method,
        headers: options.headers,
        signal: controller.signal,
      };
      if (options.body !== undefined) {
        init.body = JSON.stringify(options.body);
      }
      const response = await fetch(url, init);
      return {
        status: response.status,
        json: () => response.json() as Promise<unknown>,
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
