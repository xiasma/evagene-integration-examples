import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { buildSnippet } from '../src/snippetBuilder.js';

const REQUEST = {
  embedUrl: 'https://evagene.net/api/embed/abc?api_key=evg_x',
  label: 'Family pedigree',
  mintedAt: '2026-04-20T12:00:00.000Z',
  plaintextKey: 'evg_x',
  revokeUrl: 'https://evagene.net/account/api-keys',
} as const;

test('emits an iframe with the embed URL as src', () => {
  const html = buildSnippet(REQUEST);

  ok(html.includes(`<iframe src="${REQUEST.embedUrl}"`));
});

test('emits the label as iframe title', () => {
  const html = buildSnippet(REQUEST);

  ok(html.includes(`title="Family pedigree"`));
});

test('escapes quotes in the label', () => {
  const html = buildSnippet({ ...REQUEST, label: 'Mum\'s "pedigree"' });

  ok(html.includes('title="Mum\'s &quot;pedigree&quot;"'));
  ok(!html.includes('title="Mum\'s "pedigree""'));
});

test('escapes HTML-significant characters in the embed URL', () => {
  const html = buildSnippet({
    ...REQUEST,
    embedUrl: 'https://evagene.net/api/embed/abc?api_key=evg_x&foo=<bar>',
  });

  ok(html.includes('api_key=evg_x&amp;foo=&lt;bar&gt;'));
});

test('includes the minted key and the revoke URL in the trailing note', () => {
  const html = buildSnippet(REQUEST);

  const lines = html.split('\n');
  const note = lines.find(line => line.startsWith('Minted API key:'));
  ok(note !== undefined);
  ok(note.includes('evg_x'));
  ok(note.includes('https://evagene.net/account/api-keys'));
});

test('opening comment records when the key was minted', () => {
  const html = buildSnippet(REQUEST);
  const firstLine = html.split('\n')[0] ?? '';

  ok(firstLine.startsWith('<!--'));
  ok(firstLine.includes(REQUEST.mintedAt));
});

test('separates snippet and note with a blank line', () => {
  const lines = buildSnippet(REQUEST).split('\n');
  const iframeIndex = lines.findIndex(line => line.startsWith('<iframe'));
  strictEqual(lines[iframeIndex + 1], '');
});
