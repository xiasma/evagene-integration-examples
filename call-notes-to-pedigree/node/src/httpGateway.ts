/**
 * HTTP gateway abstraction and a `fetch`-backed implementation.
 */

export interface HttpResponse {
  readonly status: number;
  text(): Promise<string>;
  json(): Promise<unknown>;
}

export interface HttpGatewayOptions {
  readonly method: 'POST' | 'PATCH' | 'DELETE';
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body: unknown;
}

export interface HttpGateway {
  send(options: HttpGatewayOptions): Promise<HttpResponse>;
}

export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 30_000) {}

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
      const text = await response.text();
      return {
        status: response.status,
        text: () => Promise.resolve(text),
        json: () => Promise.resolve(text === '' ? null : (JSON.parse(text) as unknown)),
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
