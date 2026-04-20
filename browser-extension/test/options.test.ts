import { strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { validatePattern } from '../src/patternValidator.js';

test('accepts the default UUID pattern', () => {
  const result = validatePattern(
    '\\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\b',
  );
  strictEqual(result.ok, true);
});

test('rejects a pattern that matches short numeric tokens', () => {
  const result = validatePattern('\\d+');
  strictEqual(result.ok, false);
});

test('rejects a pattern that matches any word', () => {
  const result = validatePattern('\\w+');
  strictEqual(result.ok, false);
});

test('rejects invalid regex syntax', () => {
  const result = validatePattern('[unclosed');
  strictEqual(result.ok, false);
});

test('rejects the empty string', () => {
  const result = validatePattern('   ');
  strictEqual(result.ok, false);
});

test('accepts an EHR-specific pattern with a fixed prefix', () => {
  const result = validatePattern('\\bMRN-[0-9]{8}\\b');
  strictEqual(result.ok, true);
});
