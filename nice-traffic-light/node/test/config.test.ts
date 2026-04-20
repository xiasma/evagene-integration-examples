import { strictEqual, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { ConfigError, loadConfig } from '../src/config.js';

const VALID_UUID = '11111111-1111-1111-1111-111111111111';

test('defaults base URL when env is unset', () => {
  const config = loadConfig([VALID_UUID], { EVAGENE_API_KEY: 'evg_test' });

  strictEqual(config.baseUrl, 'https://evagene.net');
  strictEqual(config.apiKey, 'evg_test');
  strictEqual(config.pedigreeId, VALID_UUID);
  strictEqual(config.counseleeId, undefined);
});

test('honours custom base URL', () => {
  const config = loadConfig([VALID_UUID], {
    EVAGENE_API_KEY: 'evg_test',
    EVAGENE_BASE_URL: 'https://evagene.example',
  });

  strictEqual(config.baseUrl, 'https://evagene.example');
});

test('missing API key throws', () => {
  throws(() => loadConfig([VALID_UUID], {}), ConfigError);
});

test('pedigree id must be a UUID', () => {
  throws(() => loadConfig(['not-a-uuid'], { EVAGENE_API_KEY: 'evg_test' }), ConfigError);
});

test('counselee must be a UUID when provided', () => {
  throws(
    () => loadConfig([VALID_UUID, '--counselee', 'oops'], { EVAGENE_API_KEY: 'evg_test' }),
    ConfigError,
  );
});
