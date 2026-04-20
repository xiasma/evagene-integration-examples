import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { ChatReport } from '../src/handlers.js';
import { renderTeams, renderTeamsError } from '../src/renderTeams.js';

function report(overrides: Partial<ChatReport> = {}): ChatReport {
  return {
    summary: {
      pedigreeId: 'a1cfe665-0000-4000-8000-000000000001',
      displayName: 'Windsor BRCA branch',
      probandName: 'Elizabeth',
    },
    nice: {
      category: 'AMBER',
      referForGeneticsAssessment: true,
      triggers: ['Cousin affected <50'],
    },
    links: {
      webUrl: 'https://evagene.example/pedigrees/a1cfe665-0000-4000-8000-000000000001',
      svgUrl: 'https://evagene.example/api/pedigrees/a1cfe665-0000-4000-8000-000000000001/export.svg',
    },
    ...overrides,
  };
}

test('renders a MessageCard with theme, facts, and two OpenUri actions', () => {
  const response = renderTeams(report());

  strictEqual(response['@type'], 'MessageCard');
  strictEqual(response['@context'], 'https://schema.org/extensions');
  strictEqual(response.themeColor, 'F5A623');
  strictEqual(response.title, 'Windsor BRCA branch');
  strictEqual(response.text.includes('AMBER'), true);

  const facts = response.sections[0]?.facts ?? [];
  deepStrictEqual(
    facts.map(fact => fact.name),
    ['NICE category', 'Proband'],
  );

  deepStrictEqual(
    response.potentialAction.map(action => action.targets[0]?.uri),
    [report().links.webUrl, report().links.svgUrl],
  );
});

test('uses the GREEN theme colour for near-population risk', () => {
  const response = renderTeams(
    report({ nice: { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] } }),
  );
  strictEqual(response.themeColor, '2EB886');
});

test('uses the RED theme colour for high risk', () => {
  const response = renderTeams(
    report({ nice: { category: 'RED', referForGeneticsAssessment: true, triggers: [] } }),
  );
  strictEqual(response.themeColor, 'D0021B');
});

test('omits the triggers section when there are no triggers', () => {
  const response = renderTeams(
    report({ nice: { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] } }),
  );
  strictEqual(response.sections.length, 1);
});

test('omits the Proband fact when no proband is designated', () => {
  const response = renderTeams(
    report({
      summary: { pedigreeId: 'x', displayName: 'Unnamed', probandName: undefined },
    }),
  );
  deepStrictEqual(
    response.sections[0]?.facts?.map(fact => fact.name),
    ['NICE category'],
  );
});

test('renderTeamsError produces a minimal card with the message', () => {
  const response = renderTeamsError('Signature check failed; request ignored.');
  strictEqual(response['@type'], 'MessageCard');
  strictEqual(response.text, 'Signature check failed; request ignored.');
  strictEqual(response.potentialAction.length, 0);
});
