export interface HttpResponse {
  readonly status: number;
  json(): Promise<unknown>;
}

export interface HttpGatewayOptions {
  readonly method: 'POST' | 'PATCH';
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body: unknown;
}

export interface HttpGateway {
  send(options: HttpGatewayOptions): Promise<HttpResponse>;
}

/** Thin adapter over the built-in `fetch`. */
export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 10_000) {}

  async send(options: HttpGatewayOptions): Promise<HttpResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);
    try {
      const response = await fetch(options.url, {
        method: options.method,
        headers: options.headers,
        body: JSON.stringify(options.body),
        signal: controller.signal,
      });
      return {
        status: response.status,
        json: () => response.json() as Promise<unknown>,
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
