import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { EXIT_OK, EXIT_UNAVAILABLE, EXIT_USAGE, run } from '../src/app.js';
import type { Clock } from '../src/clock.js';
import type { HttpGateway, HttpGatewayOptions, HttpResponse } from '../src/httpGateway.js';
import type { TextSink } from '../src/presenter.js';

const PEDIGREE_ID = 'a1cfe665-2e95-4386-9eb8-53d46095478a';
const MINTED_KEY_ID = '22222222-2222-2222-2222-222222222222';
const FIXED_EPOCH = 1_713_600_000;
const FIXED_ISO = '2024-04-20T07:11:40.000Z';

class CapturingSink implements TextSink {
  private buffer = '';
  write(text: string): void {
    this.buffer += text;
  }
  value(): string {
    return this.buffer;
  }
}

class StubClock implements Clock {
  nowIso(): string {
    return FIXED_ISO;
  }
  nowEpochSeconds(): number {
    return FIXED_EPOCH;
  }
}

class StubGateway implements HttpGateway {
  lastBody: unknown = undefined;

  constructor(private readonly response: HttpResponse) {}

  postJson(_url: string, options: HttpGatewayOptions): Promise<HttpResponse> {
    this.lastBody = options.body;
    return Promise.resolve(this.response);
  }
}

function okResponse(): HttpResponse {
  return {
    status: 201,
    json: () =>
      Promise.resolve({
        key: 'evg_minted_happy_path',
        api_key: { id: MINTED_KEY_ID, scopes: ['read'] },
      }),
  };
}

function failingResponse(): HttpResponse {
  return { status: 500, json: () => Promise.resolve({}) };
}

test('happy path prints an iframe and exits 0', async () => {
  const stdout = new CapturingSink();
  const stderr = new CapturingSink();
  const gateway = new StubGateway(okResponse());

  const exitCode = await run(
    [PEDIGREE_ID],
    { EVAGENE_API_KEY: 'evg_parent' },
    { stdout, stderr },
    { gateway, clock: new StubClock() },
  );

  strictEqual(exitCode, EXIT_OK);
  ok(stdout.value().includes(`<iframe src="https://evagene.net/api/embed/${PEDIGREE_ID}`));
  ok(stdout.value().includes('evg_minted_happy_path'));
  strictEqual(stderr.value(), '');
});

test('default key name uses timestamp suffix when --name omitted', async () => {
  const stdout = new CapturingSink();
  const stderr = new CapturingSink();
  const gateway = new StubGateway(okResponse());

  await run(
    [PEDIGREE_ID],
    { EVAGENE_API_KEY: 'evg_parent' },
    { stdout, stderr },
    { gateway, clock: new StubClock() },
  );

  const body = gateway.lastBody as { name: string };
  strictEqual(body.name, `share-${PEDIGREE_ID.slice(0, 8)}-${FIXED_EPOCH.toString()}`);
});

test('missing API key exits 64 and writes to stderr', async () => {
  const stdout = new CapturingSink();
  const stderr = new CapturingSink();
  const gateway = new StubGateway(okResponse());

  const exitCode = await run(
    [PEDIGREE_ID],
    {},
    { stdout, stderr },
    { gateway, clock: new StubClock() },
  );

  strictEqual(exitCode, EXIT_USAGE);
  ok(stderr.value().includes('EVAGENE_API_KEY'));
  strictEqual(stdout.value(), '');
});

test('API failure exits 69 and writes to stderr', async () => {
  const stdout = new CapturingSink();
  const stderr = new CapturingSink();
  const gateway = new StubGateway(failingResponse());

  const exitCode = await run(
    [PEDIGREE_ID],
    { EVAGENE_API_KEY: 'evg_parent' },
    { stdout, stderr },
    { gateway, clock: new StubClock() },
  );

  strictEqual(exitCode, EXIT_UNAVAILABLE);
  ok(stderr.value().includes('HTTP 500'));
});
