import { strictEqual, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { ConfigError, DEFAULT_BASE_URL, DEFAULT_OUTPUT_DIR, loadConfig } from '../src/config.js';

const VALID_UUID = '11111111-1111-1111-1111-111111111111';
const TEMPLATE_UUID = '22222222-2222-2222-2222-222222222222';

test('defaults base URL and output directory when flags are absent', () => {
  const config = loadConfig([VALID_UUID], { EVAGENE_API_KEY: 'evg_test' });

  strictEqual(config.baseUrl, DEFAULT_BASE_URL);
  strictEqual(config.outputDir, DEFAULT_OUTPUT_DIR);
  strictEqual(config.templateId, undefined);
  strictEqual(config.dryRun, false);
});

test('honours custom base URL from the environment', () => {
  const config = loadConfig([VALID_UUID], {
    EVAGENE_API_KEY: 'evg_test',
    EVAGENE_BASE_URL: 'https://evagene.example',
  });

  strictEqual(config.baseUrl, 'https://evagene.example');
});

test('honours output dir, template override, and dry-run flags', () => {
  const config = loadConfig(
    [VALID_UUID, '--output-dir', '/tmp/letters', '--template', TEMPLATE_UUID, '--dry-run'],
    { EVAGENE_API_KEY: 'evg_test' },
  );

  strictEqual(config.outputDir, '/tmp/letters');
  strictEqual(config.templateId, TEMPLATE_UUID);
  strictEqual(config.dryRun, true);
});

test('missing API key throws', () => {
  throws(() => loadConfig([VALID_UUID], {}), ConfigError);
});

test('pedigree id must be a UUID', () => {
  throws(() => loadConfig(['not-a-uuid'], { EVAGENE_API_KEY: 'evg_test' }), ConfigError);
});

test('template override must be a UUID when provided', () => {
  throws(
    () =>
      loadConfig([VALID_UUID, '--template', 'oops'], {
        EVAGENE_API_KEY: 'evg_test',
      }),
    ConfigError,
  );
});
