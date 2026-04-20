export interface HttpResponse {
  readonly status: number;
  text(): Promise<string>;
}

export interface HttpGatewayOptions {
  readonly headers: Record<string, string>;
}

export interface HttpGateway {
  getText(url: string, options: HttpGatewayOptions): Promise<HttpResponse>;
}

/** Thin adapter over the built-in `fetch`. */
export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 10_000) {}

  async getText(url: string, options: HttpGatewayOptions): Promise<HttpResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: options.headers,
        signal: controller.signal,
      });
      return {
        status: response.status,
        text: () => response.text(),
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
