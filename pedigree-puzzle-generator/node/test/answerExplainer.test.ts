import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { explain } from '../src/answerExplainer.js';
import { type Mode, MODES } from '../src/inheritance.js';
import { buildBlueprint } from '../src/puzzleBlueprint.js';

const EXPECTED_PHRASES: Readonly<Record<Mode, readonly string[]>> = {
  AD: ['AD', 'Autosomal Dominant', 'male-to-male'],
  AR: ['AR', 'Autosomal Recessive', 'carriers'],
  XLR: ['XLR', 'X-linked Recessive', 'male-to-male'],
  XLD: ['XLD', 'X-linked Dominant', 'Every daughter of an affected father'],
  MT: ['MT', 'Mitochondrial', 'matrilineal'],
};

for (const mode of MODES) {
  test(`${mode} answer contains mode name and signature phrases`, () => {
    const blueprint = buildBlueprint({ mode, generations: 3, size: 'medium', seed: 42 });
    const markdown = explain(blueprint, 'Example Condition');
    for (const phrase of EXPECTED_PHRASES[mode]) {
      ok(markdown.includes(phrase), `expected ${phrase} in ${mode} answer`);
    }
  });
}

test('answer mentions the disease display name', () => {
  const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'medium', seed: 1 });
  const markdown = explain(blueprint, "Huntington's Disease");
  ok(markdown.includes("Huntington's Disease"));
});

test('answer is well-formed Markdown with headings', () => {
  const blueprint = buildBlueprint({ mode: 'AR', generations: 3, size: 'medium', seed: 1 });
  const markdown = explain(blueprint, 'Cystic Fibrosis');
  strictEqual(markdown.startsWith('# Answer: AR'), true);
  ok(markdown.includes('## Why this mode fits'));
  ok(markdown.includes('## Teaching note'));
});
