import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { ExtractedFamily } from '../src/extractedFamily.js';
import { present } from '../src/presenter.js';

class BufferSink {
  text = '';

  write(chunk: string): void {
    this.text += chunk;
  }
}

function sampleFamily(): ExtractedFamily {
  return {
    proband: {
      displayName: 'Emma Carter',
      biologicalSex: 'female',
      yearOfBirth: 1985,
    },
    mother: { displayName: 'Grace', yearOfBirth: 1957 },
    maternalGrandmother: {
      displayName: 'Edith',
      notes: 'Ovarian cancer, late fifties.',
    },
    siblings: [
      {
        displayName: 'Alice',
        relation: 'sister',
        yearOfBirth: 1983,
        notes: 'Breast cancer at 41.',
      },
    ],
  };
}

test('emits valid JSON followed by a preview block', () => {
  const sink = new BufferSink();

  present(sampleFamily(), sink);

  const [jsonPart, previewPart] = sink.text.split('\n\n', 2);
  ok(jsonPart !== undefined && previewPart !== undefined);
  const parsed = JSON.parse(jsonPart) as {
    proband: { display_name: string; biological_sex: string };
    siblings: { relation: string }[];
  };
  strictEqual(parsed.proband.display_name, 'Emma Carter');
  strictEqual(parsed.proband.biological_sex, 'female');
  strictEqual(parsed.siblings[0]?.relation, 'sister');
  ok(previewPart.includes('Extracted family'));
  ok(previewPart.includes('Alice'));
  ok(previewPart.includes('Breast cancer at 41.'));
});

test('omits absent relatives from the JSON block', () => {
  const sink = new BufferSink();

  present(sampleFamily(), sink);

  const jsonPart = sink.text.split('\n\n', 1)[0] ?? '';
  const parsed = JSON.parse(jsonPart) as Record<string, unknown>;
  ok(!('father' in parsed));
  ok(!('paternal_grandmother' in parsed));
});
