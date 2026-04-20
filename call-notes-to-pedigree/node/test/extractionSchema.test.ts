import { readFile } from 'node:fs/promises';
import { deepStrictEqual, ok, strictEqual, throws } from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';

import {
  ExtractionSchemaError,
  buildToolSchema,
  parseExtraction,
} from '../src/extractionSchema.js';

const FIXTURE = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  'fixtures',
  'sample-extraction.json',
);

async function loadSample(): Promise<unknown> {
  const raw = await readFile(FIXTURE, 'utf8');
  return JSON.parse(raw) as unknown;
}

test('tool schema has name, description and input_schema', () => {
  const tool = buildToolSchema();

  strictEqual(tool.name, 'record_extracted_family');
  ok(tool.description.length > 0);
  const input = tool.input_schema as Record<string, unknown>;
  strictEqual(input.type, 'object');
  deepStrictEqual(input.required, ['proband', 'siblings']);
  const properties = input.properties as Record<string, unknown>;
  deepStrictEqual(
    Object.keys(properties).sort(),
    [
      'father',
      'maternal_grandfather',
      'maternal_grandmother',
      'mother',
      'paternal_grandfather',
      'paternal_grandmother',
      'proband',
      'siblings',
    ].sort(),
  );
});

test('parses the sample extraction fixture', async () => {
  const family = parseExtraction(await loadSample());

  strictEqual(family.proband.displayName, 'Emma Carter');
  strictEqual(family.proband.biologicalSex, 'female');
  strictEqual(family.proband.yearOfBirth, 1985);
  strictEqual(family.mother?.displayName, 'Grace');
  ok(family.maternalGrandmother?.notes?.includes('Ovarian cancer'));
  strictEqual(family.siblings.length, 2);
  strictEqual(family.siblings[0]?.relation, 'sister');
  strictEqual(family.siblings[1]?.relation, 'half_brother');
});

test('rejects payload missing proband', () => {
  throws(() => parseExtraction({ siblings: [] }), ExtractionSchemaError);
});

test('rejects unknown biological sex', () => {
  throws(
    () =>
      parseExtraction({
        proband: { display_name: 'Emma', biological_sex: 'robot' },
        siblings: [],
      }),
    ExtractionSchemaError,
  );
});

test('blank notes are treated as absent', () => {
  const family = parseExtraction({
    proband: { display_name: 'Emma', biological_sex: 'female', notes: '   ' },
    siblings: [],
  });
  strictEqual(family.proband.notes, undefined);
});
