import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

import type { RegisterData, RegisterRow } from '../src/evageneClient.js';
import { selectAtRiskRelatives } from '../src/relativeSelector.js';

const FIXTURES = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'fixtures');

interface FixtureRow {
  individual_id: string;
  display_name: string;
  relationship_to_proband: string;
}

interface Fixture {
  proband_id: string;
  rows: FixtureRow[];
}

function row(
  relationship: string,
  displayName = 'Someone',
  individualId = 'b0000000-0000-0000-0000-000000000001',
): RegisterRow {
  return { individualId, displayName, relationshipToProband: relationship };
}

function register(rows: RegisterRow[], probandId: string | null = null): RegisterData {
  return { probandId, rows };
}

test('selects first- and second-degree relatives from the BRCA fixture', () => {
  const raw = JSON.parse(readFileSync(`${FIXTURES}/sample-register.json`, 'utf-8')) as Fixture;
  const data: RegisterData = {
    probandId: raw.proband_id,
    rows: raw.rows.map(r => ({
      individualId: r.individual_id,
      displayName: r.display_name,
      relationshipToProband: r.relationship_to_proband,
    })),
  };

  const names = selectAtRiskRelatives(data).map(t => t.displayName);

  deepStrictEqual(names, [
    'Margaret Ward',
    'David Ward',
    'Sarah Ward',
    'Thomas Ward',
    'Joan Pembroke',
    'Elizabeth Pembroke',
  ]);
});

test('skips the proband', () => {
  const probandId = 'b0000000-0000-0000-0000-000000000042';
  const data = register(
    [
      {
        individualId: probandId,
        displayName: 'Proband',
        relationshipToProband: 'Proband',
      },
    ],
    probandId,
  );

  strictEqual(selectAtRiskRelatives(data).length, 0);
});

test('skips rows with a blank display name', () => {
  strictEqual(selectAtRiskRelatives(register([row('Sister', '   ')])).length, 0);
});

test('accepts side-suffixed second-degree labels', () => {
  const data = register([
    row('Grandmother (maternal)', 'Maternal Grandma', 'id-1'),
    row('Uncle (paternal)', 'Paternal Uncle', 'id-2'),
  ]);

  deepStrictEqual(
    selectAtRiskRelatives(data).map(t => t.displayName),
    ['Maternal Grandma', 'Paternal Uncle'],
  );
});

test('rejects third-degree and more-distant relationships', () => {
  const data = register([
    row('Great-Grandmother (maternal)', 'GGM', 'id-1'),
    row('First cousin (paternal)', 'Cousin', 'id-2'),
    row('Great-uncle (maternal)', 'GU', 'id-3'),
  ]);

  strictEqual(selectAtRiskRelatives(data).length, 0);
});

test('rejects rows with an empty relationship label', () => {
  strictEqual(selectAtRiskRelatives(register([row('', 'Mystery')])).length, 0);
});

test('accepts every first-degree base label', () => {
  const labels = [
    'Father',
    'Mother',
    'Parent',
    'Brother',
    'Sister',
    'Sibling',
    'Son',
    'Daughter',
  ];
  const data = register(labels.map((label, idx) => row(label, `Person ${label}`, `id-${idx.toString()}`)));

  strictEqual(selectAtRiskRelatives(data).length, labels.length);
});
