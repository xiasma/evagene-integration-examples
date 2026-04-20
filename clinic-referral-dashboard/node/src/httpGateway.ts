/**
 * Minimal HTTP surface so EvageneClient can be tested without network.
 * Implementations need only provide what the client actually calls:
 * GET returning text, and POST returning JSON.
 */

export interface TextResponse {
  readonly status: number;
  text(): Promise<string>;
}

export interface JsonResponse {
  readonly status: number;
  json(): Promise<unknown>;
}

export interface HttpGateway {
  getText(url: string, headers: Readonly<Record<string, string>>): Promise<TextResponse>;
  postJson(
    url: string,
    headers: Readonly<Record<string, string>>,
    body: unknown,
  ): Promise<JsonResponse>;
}

/** Thin adapter over the built-in `fetch`. */
export class FetchHttpGateway implements HttpGateway {
  constructor(private readonly timeoutMs = 10_000) {}

  async getText(
    url: string,
    headers: Readonly<Record<string, string>>,
  ): Promise<TextResponse> {
    const response = await this.request(url, { method: 'GET', headers });
    return {
      status: response.status,
      text: () => response.text(),
    };
  }

  async postJson(
    url: string,
    headers: Readonly<Record<string, string>>,
    body: unknown,
  ): Promise<JsonResponse> {
    const response = await this.request(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    return {
      status: response.status,
      json: () => response.json() as Promise<unknown>,
    };
  }

  private async request(url: string, init: RequestInit): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);
    try {
      return await fetch(url, { ...init, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }
}
