/**
 * Render an {@link ExtractedFamily} as pretty JSON plus a readable preview.
 */

import type {
  ExtractedFamily,
  RelativeEntry,
  SiblingEntry,
} from './extractedFamily.js';

export interface TextSink {
  write(text: string): void;
}

const RELATIVE_LABELS: readonly { readonly key: RelativeKey; readonly label: string }[] = [
  { key: 'mother', label: 'mother' },
  { key: 'father', label: 'father' },
  { key: 'maternalGrandmother', label: 'maternal grandmother' },
  { key: 'maternalGrandfather', label: 'maternal grandfather' },
  { key: 'paternalGrandmother', label: 'paternal grandmother' },
  { key: 'paternalGrandfather', label: 'paternal grandfather' },
];

type RelativeKey =
  | 'mother'
  | 'father'
  | 'maternalGrandmother'
  | 'maternalGrandfather'
  | 'paternalGrandmother'
  | 'paternalGrandfather';

export function present(family: ExtractedFamily, sink: TextSink): void {
  sink.write(toJson(family));
  sink.write('\n\n');
  sink.write(toPreview(family));
  sink.write('\n');
}

function toJson(family: ExtractedFamily): string {
  return JSON.stringify(asPlainObject(family), null, 2);
}

function asPlainObject(family: ExtractedFamily): Record<string, unknown> {
  const out: Record<string, unknown> = {
    proband: withNulls(family.proband as unknown as Record<string, unknown>, [
      'displayName',
      'biologicalSex',
      'yearOfBirth',
      'notes',
    ]),
  };
  for (const { key } of RELATIVE_LABELS) {
    const entry = family[key];
    if (entry !== undefined) {
      out[snakeCase(key)] = withNulls(entry as unknown as Record<string, unknown>, [
        'displayName',
        'yearOfBirth',
        'notes',
      ]);
    }
  }
  out.siblings = family.siblings.map(sibling =>
    withNulls(sibling as unknown as Record<string, unknown>, [
      'displayName',
      'relation',
      'yearOfBirth',
      'notes',
    ]),
  );
  return out;
}

function withNulls(
  value: Record<string, unknown>,
  keys: readonly string[],
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const key of keys) {
    const raw = value[key];
    result[snakeCase(key)] = raw === undefined ? null : raw;
  }
  return result;
}

function snakeCase(camel: string): string {
  return camel.replace(/[A-Z]/g, match => `_${match.toLowerCase()}`);
}

function toPreview(family: ExtractedFamily): string {
  const lines: string[] = ['Extracted family'];
  const proband = family.proband;
  lines.push(
    `  proband  ${proband.displayName} (${proband.biologicalSex}${formatYear(proband.yearOfBirth)})`,
  );
  for (const { key, label } of RELATIVE_LABELS) {
    const entry = family[key];
    if (entry !== undefined) {
      lines.push(`  ${label.padEnd(22)} ${formatRelative(entry)}`);
    }
  }
  if (family.siblings.length > 0) {
    lines.push('  siblings');
    for (const sibling of family.siblings) {
      lines.push(`    - ${formatSibling(sibling)}`);
    }
  }
  return lines.join('\n');
}

function formatRelative(entry: RelativeEntry): string {
  return withNotes(`${entry.displayName}${formatYear(entry.yearOfBirth)}`, entry.notes);
}

function formatSibling(sibling: SiblingEntry): string {
  const header = `${sibling.displayName} (${sibling.relation}${formatYear(sibling.yearOfBirth)})`;
  return withNotes(header, sibling.notes);
}

function formatYear(year: number | undefined): string {
  return year === undefined ? '' : `, b.${year.toString()}`;
}

function withNotes(header: string, notes: string | undefined): string {
  return notes !== undefined && notes !== '' ? `${header} -- ${notes}` : header;
}
