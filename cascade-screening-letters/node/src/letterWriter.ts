/**
 * Compose a per-relative Markdown letter and hand it to a sink.
 *
 * Composition is local because the Evagene template-run endpoint operates
 * at pedigree level: it cannot vary its output per relative.  The
 * personalised salutation and relationship sentence are added here; the
 * template body sits in between.
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import type { LetterTarget } from './relativeSelector.js';

const MAX_SLUG_LENGTH = 60;
const NON_SLUG = /[^a-z0-9]+/g;
const INDEX_PAD_WIDTH = 2;

export interface LetterFile {
  readonly filename: string;
  readonly content: string;
}

export interface LetterSink {
  write(letter: LetterFile): string;
}

export class DiskLetterSink implements LetterSink {
  constructor(private readonly outputDir: string) {}

  write(letter: LetterFile): string {
    mkdirSync(this.outputDir, { recursive: true });
    const fullPath = join(this.outputDir, letter.filename);
    writeFileSync(fullPath, letter.content, 'utf-8');
    return fullPath.replaceAll('\\', '/');
  }
}

export function composeLetter(
  target: LetterTarget,
  templateBody: string,
  index: number,
): LetterFile {
  return {
    filename: filenameFor(target, index),
    content: markdownFor(target, templateBody),
  };
}

function filenameFor(target: LetterTarget, index: number): string {
  return `${index.toString().padStart(INDEX_PAD_WIDTH, '0')}-${slugify(target.displayName)}.md`;
}

function slugify(name: string): string {
  const lowered = name.trim().toLowerCase();
  const slug = lowered.replace(NON_SLUG, '-').replace(/^-+|-+$/g, '');
  if (slug === '') {
    return 'relative';
  }
  const truncated = slug.slice(0, MAX_SLUG_LENGTH).replace(/-+$/, '');
  return truncated === '' ? 'relative' : truncated;
}

function markdownFor(target: LetterTarget, templateBody: string): string {
  return (
    `# Cascade screening invitation\n\n` +
    `Dear ${target.displayName},\n\n` +
    `You are recorded as the **${target.relationship.toLowerCase()}** of the person ` +
    `whose family has had a genetic result identified. The paragraphs below were ` +
    `drafted automatically and should be reviewed by your genetic counsellor before ` +
    `this letter is sent.\n\n` +
    `${templateBody.replace(/\s+$/, '')}\n\n` +
    `Yours sincerely,\n\n` +
    `The Clinical Genetics Team\n`
  );
}
