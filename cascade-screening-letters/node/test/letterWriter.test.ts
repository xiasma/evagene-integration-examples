import { ok, strictEqual } from 'node:assert/strict';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { DiskLetterSink, composeLetter } from '../src/letterWriter.js';
import type { LetterTarget } from '../src/relativeSelector.js';

function target(displayName = 'Sarah Ward', relationship = 'Sister'): LetterTarget {
  return {
    individualId: 'b0000000-0000-0000-0000-000000000001',
    displayName,
    relationship,
  };
}

test('filename uses two-digit index and slug', () => {
  const letter = composeLetter(target(), 'Body.', 3);

  strictEqual(letter.filename, '03-sarah-ward.md');
});

test('filename strips punctuation and collapses whitespace', () => {
  const letter = composeLetter(target("O'Brien,  Mary Jane!"), 'Body.', 1);

  strictEqual(letter.filename, '01-o-brien-mary-jane.md');
});

test('filename has no path separators even for malicious names', () => {
  const letter = composeLetter(target('../../etc/passwd'), 'Body.', 1);

  ok(!letter.filename.includes('/'));
  ok(!letter.filename.includes('\\'));
  ok(!letter.filename.includes('..'));
});

test('filename falls back when the name slugifies to empty', () => {
  const letter = composeLetter(target('...'), 'Body.', 1);

  strictEqual(letter.filename, '01-relative.md');
});

test('content contains relative name, relationship, and body', () => {
  const letter = composeLetter(
    target('Sarah Ward', 'Sister'),
    'Dear reader, this is the template-generated body.',
    1,
  );

  ok(letter.content.includes('Dear Sarah Ward'));
  ok(letter.content.includes('sister'));
  ok(letter.content.includes('template-generated body'));
  ok(letter.content.endsWith('The Clinical Genetics Team\n'));
});

test('disk sink writes the letter and reports the POSIX-style path', () => {
  const dir = mkdtempSync(join(tmpdir(), 'cascade-node-'));
  const sink = new DiskLetterSink(join(dir, 'letters'));

  const reported = sink.write({ filename: '01-jane.md', content: 'Hello.\n' });

  const expectedPath = join(dir, 'letters', '01-jane.md');
  strictEqual(readFileSync(expectedPath, 'utf-8'), 'Hello.\n');
  strictEqual(reported, expectedPath.replaceAll('\\', '/'));
});

test('disk sink creates nested parent directories', () => {
  const dir = mkdtempSync(join(tmpdir(), 'cascade-node-'));
  const sink = new DiskLetterSink(join(dir, 'nested', 'letters'));

  sink.write({ filename: '01-a.md', content: 'x' });

  strictEqual(readFileSync(join(dir, 'nested', 'letters', '01-a.md'), 'utf-8'), 'x');
});
