import { strictEqual, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { ConfigError, loadConfig } from '../src/config.js';

test('parses minimal valid inputs', () => {
  const config = loadConfig(
    ['--mode', 'AR', '--seed', '42'],
    { EVAGENE_API_KEY: 'evg_test' },
  );
  strictEqual(config.mode, 'AR');
  strictEqual(config.generations, 3);
  strictEqual(config.size, 'medium');
  strictEqual(config.apiKey, 'evg_test');
  strictEqual(config.baseUrl, 'https://evagene.net');
  strictEqual(config.outputDir, './puzzles');
  strictEqual(config.cleanup, true);
  strictEqual(config.seed, 42);
});

test('random mode keeps mode as null', () => {
  const config = loadConfig([], { EVAGENE_API_KEY: 'evg_test' });
  strictEqual(config.mode, null);
});

test('--no-cleanup flag disables cleanup', () => {
  const config = loadConfig(['--no-cleanup'], { EVAGENE_API_KEY: 'evg_test' });
  strictEqual(config.cleanup, false);
});

test('missing API key is a usage error', () => {
  throws(() => loadConfig([], {}), ConfigError);
});

test('invalid mode is a usage error', () => {
  throws(
    () => loadConfig(['--mode', 'NOPE'], { EVAGENE_API_KEY: 'evg_test' }),
    ConfigError,
  );
});

test('invalid generations is a usage error', () => {
  throws(
    () => loadConfig(['--generations', '5'], { EVAGENE_API_KEY: 'evg_test' }),
    ConfigError,
  );
});

test('invalid size is a usage error', () => {
  throws(
    () => loadConfig(['--size', 'huge'], { EVAGENE_API_KEY: 'evg_test' }),
    ConfigError,
  );
});

test('base URL can be overridden via env', () => {
  const config = loadConfig([], {
    EVAGENE_API_KEY: 'evg_test',
    EVAGENE_BASE_URL: 'http://localhost:8000',
  });
  strictEqual(config.baseUrl, 'http://localhost:8000');
});
