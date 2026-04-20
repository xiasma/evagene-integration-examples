/**
 * Write the question and answer Markdown pair into a timestamped folder.
 */

import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

import { MODES, modeFullName } from './inheritance.js';
import { findIndividual, type PedigreeBlueprint } from './puzzleBlueprint.js';

export interface PuzzleArtefact {
  readonly folder: string;
  readonly questionPath: string;
  readonly answerPath: string;
}

export interface WritePuzzleArgs {
  readonly outputDir: string;
  readonly timestamp: Date;
  readonly blueprint: PedigreeBlueprint;
  readonly diseaseDisplayName: string;
  readonly pedigreeId: string;
  readonly evageneBaseUrl: string;
  readonly svg: string;
  readonly answerMarkdown: string;
}

export async function writePuzzle(args: WritePuzzleArgs): Promise<PuzzleArtefact> {
  const folder = path.join(args.outputDir, `puzzle-${slugTimestamp(args.timestamp)}`);
  await mkdir(args.outputDir, { recursive: true });
  await mkdir(folder, { recursive: false });

  const svgPath = path.join(folder, 'pedigree.svg');
  await writeFile(svgPath, args.svg, 'utf-8');

  const questionPath = path.join(folder, 'question.md');
  await writeFile(
    questionPath,
    questionMarkdown({
      blueprint: args.blueprint,
      pedigreeId: args.pedigreeId,
      evageneBaseUrl: args.evageneBaseUrl,
      svgFileName: path.basename(svgPath),
    }),
    'utf-8',
  );

  const answerPath = path.join(folder, 'answer.md');
  await writeFile(answerPath, args.answerMarkdown, 'utf-8');

  // diseaseDisplayName is consumed by answerExplainer upstream; we
  // deliberately do not repeat it in question.md to avoid spoilers.
  void args.diseaseDisplayName;

  return { folder, questionPath, answerPath };
}

function slugTimestamp(timestamp: Date): string {
  const utc = new Date(timestamp.toISOString());
  const year = utc.getUTCFullYear().toString().padStart(4, '0');
  const month = (utc.getUTCMonth() + 1).toString().padStart(2, '0');
  const day = utc.getUTCDate().toString().padStart(2, '0');
  const hour = utc.getUTCHours().toString().padStart(2, '0');
  const minute = utc.getUTCMinutes().toString().padStart(2, '0');
  const second = utc.getUTCSeconds().toString().padStart(2, '0');
  return `${year}${month}${day}-${hour}${minute}${second}`;
}

function questionMarkdown(args: {
  readonly blueprint: PedigreeBlueprint;
  readonly pedigreeId: string;
  readonly evageneBaseUrl: string;
  readonly svgFileName: string;
}): string {
  const proband = findIndividual(args.blueprint, args.blueprint.probandId);
  const url = `${args.evageneBaseUrl}/pedigrees/${args.pedigreeId}`;
  const lines = [
    '# Pedigree puzzle',
    '',
    `![Pedigree](${args.svgFileName})`,
    '',
    `**Proband:** ${proband.displayName} ` +
      `(${proband.sex}, generation ${String(proband.generation)}).`,
    '',
    `Explore the pedigree interactively on Evagene: [${url}](${url}).`,
    '',
    `Download the SVG: [${args.svgFileName}](${args.svgFileName}).`,
    '',
    '## Your task',
    '',
    'Study the pedigree and identify the **most likely** mode of inheritance of the shaded trait.',
    '',
    'Choose one:',
    '',
    ...MODES.map((mode) => `- ${mode} (${modeFullName(mode)})`),
    '',
    'Justify your choice using the features of the pedigree ' +
      '(which sexes are affected, transmission pattern across generations, ' +
      'presence of skipped generations, male-to-male transmission, etc.).',
    '',
  ];
  return lines.join('\n');
}
