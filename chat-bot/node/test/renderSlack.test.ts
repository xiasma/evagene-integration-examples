import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { ChatReport } from '../src/handlers.js';
import { renderSlack, renderSlackError } from '../src/renderSlack.js';

function report(overrides: Partial<ChatReport> = {}): ChatReport {
  return {
    summary: {
      pedigreeId: 'a1cfe665-0000-4000-8000-000000000001',
      displayName: 'Windsor BRCA branch',
      probandName: 'Elizabeth',
    },
    nice: {
      category: 'RED',
      referForGeneticsAssessment: true,
      triggers: ['Mother affected <40'],
    },
    links: {
      webUrl: 'https://evagene.example/pedigrees/a1cfe665-0000-4000-8000-000000000001',
      svgUrl: 'https://evagene.example/api/pedigrees/a1cfe665-0000-4000-8000-000000000001/export.svg',
    },
    ...overrides,
  };
}

test('renders an in_channel response with header, category, triggers, and action buttons', () => {
  const response = renderSlack(report());

  strictEqual(response.response_type, 'in_channel');
  strictEqual(response.text, 'Windsor BRCA branch - NICE RED');

  const blockTypes = response.blocks.map(block => (block as { type: string }).type);
  deepStrictEqual(blockTypes, ['header', 'context', 'section', 'section', 'actions']);

  const actions = response.blocks[4] as {
    elements: readonly { readonly text: { readonly text: string }; readonly url: string }[];
  };
  deepStrictEqual(
    actions.elements.map(element => element.text.text),
    ['View pedigree', 'Download SVG'],
  );
});

test('omits the triggers section when the list is empty', () => {
  const response = renderSlack(
    report({ nice: { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] } }),
  );

  const blockTypes = response.blocks.map(block => (block as { type: string }).type);
  deepStrictEqual(blockTypes, ['header', 'context', 'section', 'actions']);
});

test('renders a "no proband" context when probandName is missing', () => {
  const response = renderSlack(
    report({
      summary: {
        pedigreeId: 'x',
        displayName: 'Unnamed',
        probandName: undefined,
      },
    }),
  );
  const context = response.blocks[1] as {
    elements: readonly { readonly text: string }[];
  };
  strictEqual(context.elements[0]?.text, 'No proband designated.');
});

test('renderSlackError produces a minimal in_channel warning', () => {
  const response = renderSlackError('Signature check failed; request ignored.');
  strictEqual(response.response_type, 'in_channel');
  strictEqual(response.blocks.length, 1);
  strictEqual(response.text, 'Signature check failed; request ignored.');
});
