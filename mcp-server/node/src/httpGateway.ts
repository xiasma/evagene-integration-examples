export interface HttpResponse {
  readonly status: number;
  json(): Promise<unknown>;
  text(): Promise<string>;
}

export interface HttpRequestOptions {
  readonly method: 'GET' | 'POST';
  readonly headers: Record<string, string>;
  readonly body?: unknown;
}

export interface HttpGateway {
  request(url: string, options: HttpRequestOptions): Promise<HttpResponse>;
}

/** Thin adapter over the built-in `fetch`. */
export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 30_000) {}

  async request(url: string, options: HttpRequestOptions): Promise<HttpResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => { controller.abort(); }, this.timeoutMs);
    try {
      const response = await fetch(url, {
        method: options.method,
        headers: options.headers,
        ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
        signal: controller.signal,
      });
      return {
        status: response.status,
        json: () => response.json() as Promise<unknown>,
        text: () => response.text(),
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
