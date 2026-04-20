/**
 * HTTP gateway abstraction and a fetch-backed implementation.
 *
 * The abstraction is narrow (one send).  Tests inject a fake; production
 * code receives FetchHttpGateway, which also handles HTTP 429 rate-limit
 * responses by honouring the server's Retry-After header (a few retries,
 * bounded wait).  The puzzle generator makes many writes in quick
 * succession and would otherwise hit the default per-minute rate limit
 * on an interactive API key.
 */

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE';

export interface HttpResponse {
  readonly status: number;
  text(): Promise<string>;
  json(): Promise<unknown>;
}

export interface HttpGatewayOptions {
  readonly method: HttpMethod;
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body?: unknown;
}

export interface HttpGateway {
  send(options: HttpGatewayOptions): Promise<HttpResponse>;
}

export type Sleeper = (milliseconds: number) => Promise<void>;

const TOO_MANY_REQUESTS = 429;
const MAX_RETRIES = 4;
const FALLBACK_RETRY_MS = 2000;

export class FetchHttpGateway implements HttpGateway {
  constructor(
    private readonly timeoutMs = 15_000,
    private readonly sleep: Sleeper = defaultSleep,
  ) {}

  async send(options: HttpGatewayOptions): Promise<HttpResponse> {
    for (let attempt = 0; ; attempt += 1) {
      const response = await this.singleAttempt(options);
      if (response.status !== TOO_MANY_REQUESTS || attempt >= MAX_RETRIES) {
        return response;
      }
      await this.sleep(retryAfterMs(response));
    }
  }

  private async singleAttempt(options: HttpGatewayOptions): Promise<FetchResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);
    try {
      const init: RequestInit = {
        method: options.method,
        headers: options.headers,
        signal: controller.signal,
      };
      if (options.body !== undefined) {
        init.body = JSON.stringify(options.body);
      }
      const response = await fetch(options.url, init);
      return new FetchResponse(response);
    } finally {
      clearTimeout(timer);
    }
  }
}

class FetchResponse implements HttpResponse {
  constructor(private readonly underlying: Response) {}
  get status(): number {
    return this.underlying.status;
  }
  text(): Promise<string> {
    return this.underlying.text();
  }
  json(): Promise<unknown> {
    return this.underlying.json() as Promise<unknown>;
  }
  get headers(): Headers {
    return this.underlying.headers;
  }
}

function retryAfterMs(response: HttpResponse): number {
  if (!(response instanceof FetchResponse)) return FALLBACK_RETRY_MS;
  const raw = response.headers.get('Retry-After')?.trim() ?? '';
  if (raw === '') return FALLBACK_RETRY_MS;
  const seconds = Number.parseFloat(raw);
  if (!Number.isFinite(seconds) || seconds < 0) return FALLBACK_RETRY_MS;
  return Math.round(seconds * 1000);
}

function defaultSleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
