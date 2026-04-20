export interface HttpResponse {
  readonly status: number;
  json(): Promise<unknown>;
}

export interface HttpGatewayOptions {
  readonly headers: Record<string, string>;
  readonly body: unknown;
}

export interface HttpGateway {
  postJson(url: string, options: HttpGatewayOptions): Promise<HttpResponse>;
}

/** Thin adapter over the built-in `fetch`. */
export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 10_000) {}

  async postJson(url: string, options: HttpGatewayOptions): Promise<HttpResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => { controller.abort(); }, this.timeoutMs);
    try {
      const response = await fetch(url, {
        method: 'POST',
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
