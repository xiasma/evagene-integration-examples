import { strictEqual } from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { JSDOM } from 'jsdom';

import { BUTTON_CLASS, MARKER_ATTRIBUTE, annotate } from '../src/contentInjector.js';
import { DEFAULT_PATTERN } from '../src/storage.js';

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = resolve(here, '..', 'fixtures', 'sample-ehr-page.html');

async function loadFixture(): Promise<JSDOM> {
  const html = await readFile(fixturePath, 'utf8');
  return new JSDOM(html);
}

function pattern(): RegExp {
  return new RegExp(DEFAULT_PATTERN, 'g');
}

test('injects one button per UUID occurrence in the fixture', async () => {
  const dom = await loadFixture();
  const clicks: string[] = [];
  const injected = annotate({
    root: dom.window.document.body,
    pattern: pattern(),
    onClick: id => clicks.push(id),
  });

  strictEqual(injected, 3);
  const buttons = dom.window.document.querySelectorAll(`button.${BUTTON_CLASS}`);
  strictEqual(buttons.length, 3);
});

test('button click forwards the matched pedigree id', async () => {
  const dom = await loadFixture();
  const clicks: string[] = [];
  annotate({
    root: dom.window.document.body,
    pattern: pattern(),
    onClick: id => clicks.push(id),
  });
  const first = dom.window.document.querySelector(`button.${BUTTON_CLASS}`);
  strictEqual(first instanceof dom.window.HTMLButtonElement, true);
  (first as HTMLButtonElement).click();
  strictEqual(clicks[0], '7c8d4d6a-1234-4aaa-8bbb-000000000001');
});

test('re-running annotate does not double-inject', async () => {
  const dom = await loadFixture();
  annotate({
    root: dom.window.document.body,
    pattern: pattern(),
    onClick: () => undefined,
  });
  const injectedAgain = annotate({
    root: dom.window.document.body,
    pattern: pattern(),
    onClick: () => undefined,
  });
  strictEqual(injectedAgain, 0);
  strictEqual(
    dom.window.document.querySelectorAll(`button.${BUTTON_CLASS}`).length,
    3,
  );
});

test('marks annotated regions with the data attribute', async () => {
  const dom = await loadFixture();
  annotate({
    root: dom.window.document.body,
    pattern: pattern(),
    onClick: () => undefined,
  });
  const marked = dom.window.document.querySelectorAll(`[${MARKER_ATTRIBUTE}]`);
  strictEqual(marked.length > 0, true);
});
