import { readFile } from 'node:fs/promises';
import { rejects, strictEqual } from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';

import {
  AnthropicExtractor,
  type LlmRequest,
} from '../src/anthropicExtractor.js';
import { ExtractionSchemaError } from '../src/extractionSchema.js';

const FIXTURE = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  'fixtures',
  'sample-extraction.json',
);

async function loadSample(): Promise<Record<string, unknown>> {
  const raw = await readFile(FIXTURE, 'utf8');
  return JSON.parse(raw) as Record<string, unknown>;
}

class FakeGateway {
  lastRequest: LlmRequest | undefined;

  constructor(private readonly payload: Record<string, unknown>) {}

  invokeTool(request: LlmRequest): Promise<Record<string, unknown>> {
    this.lastRequest = request;
    return Promise.resolve(this.payload);
  }
}

test('extractor forwards transcript and parses payload', async () => {
  const gateway = new FakeGateway(await loadSample());
  const extractor = new AnthropicExtractor({ gateway, model: 'test-model' });

  const family = await extractor.extract('a transcript');

  strictEqual(gateway.lastRequest?.model, 'test-model');
  strictEqual(gateway.lastRequest.userPrompt, 'a transcript');
  strictEqual(gateway.lastRequest.temperature, 0);
  strictEqual(family.proband.displayName, 'Emma Carter');
  strictEqual(family.siblings.length, 2);
});

test('schema mismatch raises schema error', async () => {
  const gateway = new FakeGateway({
    proband: { display_name: 'Emma' },
    siblings: [],
  });
  const extractor = new AnthropicExtractor({ gateway });

  await rejects(extractor.extract('a transcript'), ExtractionSchemaError);
});
