import { strictEqual, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { ConfigError, loadConfig } from '../src/config.js';

test('reads API key and defaults base URL', () => {
  const config = loadConfig({ EVAGENE_API_KEY: 'evg_test' });

  strictEqual(config.apiKey, 'evg_test');
  strictEqual(config.baseUrl, 'https://evagene.net');
});

test('overrides base URL when set', () => {
  const config = loadConfig({
    EVAGENE_API_KEY: 'evg_test',
    EVAGENE_BASE_URL: 'http://localhost:8000',
  });

  strictEqual(config.baseUrl, 'http://localhost:8000');
});

test('rejects missing API key', () => {
  throws(() => loadConfig({}), ConfigError);
});

test('rejects blank API key', () => {
  throws(() => loadConfig({ EVAGENE_API_KEY: '   ' }), ConfigError);
});
