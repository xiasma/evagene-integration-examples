import { strictEqual, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { ConfigError, DEFAULT_BASE_URL, loadConfig } from '../src/config.js';

test('read-only mode needs only ANTHROPIC_API_KEY', () => {
  const config = loadConfig(['transcript.txt'], { ANTHROPIC_API_KEY: 'sk-ant-test' });

  strictEqual(config.transcriptPath, 'transcript.txt');
  strictEqual(config.commit, false);
  strictEqual(config.showPrompt, false);
  strictEqual(config.anthropicApiKey, 'sk-ant-test');
  strictEqual(config.evageneApiKey, undefined);
  strictEqual(config.evageneBaseUrl, DEFAULT_BASE_URL);
});

test('stdin mode when no file is given', () => {
  const config = loadConfig([], { ANTHROPIC_API_KEY: 'sk-ant-test' });
  strictEqual(config.transcriptPath, undefined);
});

test('--commit requires EVAGENE_API_KEY', () => {
  throws(
    () => loadConfig(['--commit'], { ANTHROPIC_API_KEY: 'sk-ant-test' }),
    ConfigError,
  );
});

test('--commit with both keys populates both', () => {
  const config = loadConfig(['--commit', 'transcript.txt'], {
    ANTHROPIC_API_KEY: 'sk-ant-test',
    EVAGENE_API_KEY: 'evg_test',
  });
  strictEqual(config.commit, true);
  strictEqual(config.evageneApiKey, 'evg_test');
});

test('--show-prompt does not require any API key', () => {
  const config = loadConfig(['--show-prompt'], {});

  strictEqual(config.showPrompt, true);
  strictEqual(config.anthropicApiKey, undefined);
  strictEqual(config.evageneApiKey, undefined);
});

test('missing ANTHROPIC_API_KEY outside --show-prompt fails', () => {
  throws(() => loadConfig([], {}), ConfigError);
});

test('--model overrides the default', () => {
  const config = loadConfig(['--model', 'claude-sonnet-4-5'], {
    ANTHROPIC_API_KEY: 'sk-ant-test',
  });
  strictEqual(config.model, 'claude-sonnet-4-5');
});

test('custom EVAGENE_BASE_URL is honoured', () => {
  const config = loadConfig([], {
    ANTHROPIC_API_KEY: 'sk-ant-test',
    EVAGENE_BASE_URL: 'https://evagene.example',
  });
  strictEqual(config.evageneBaseUrl, 'https://evagene.example');
});
