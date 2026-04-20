/**
 * Compose the answer-key Markdown for a given mode and blueprint.
 *
 * Pure: given a PedigreeBlueprint produce the educational paragraph.
 * All teaching content flows from modeHeuristics; this module only
 * arranges it.
 */

import { type Mode, modeFullName } from './inheritance.js';
import { teachingCues } from './modeHeuristics.js';
import type { PedigreeBlueprint } from './puzzleBlueprint.js';

const TEACHING_NOTES: Readonly<Record<Mode, string>> = {
  AD:
    "Textbook heuristic: 'vertical transmission plus male-to-male transmission implies " +
    "autosomal dominant.' If you see an affected son of an affected father, X-linked " +
    'modes are ruled out.',
  AR:
    "Textbook heuristic: 'unaffected parents, affected children -- think recessive.' " +
    'If both sexes are affected equally and the pattern clusters within a sibship, ' +
    'autosomal recessive is the most parsimonious explanation.',
  XLR:
    "Textbook heuristic: 'males affected across generations through unaffected females " +
    "-- carrier mothers.' No male-to-male transmission is the single strongest " +
    'discriminator from autosomal dominant.',
  XLD:
    "Textbook heuristic: 'every daughter of an affected father is affected; no son is.' " +
    'That asymmetric pattern distinguishes XLD from AD -- AD would affect sons and ' +
    'daughters in equal proportion.',
  MT:
    "Textbook heuristic: 'affected mother -> all children at risk; affected father -> " +
    "no children at risk.' Strict matrilineal transmission rules out every nuclear " +
    'inheritance mode.',
};

export function explain(blueprint: PedigreeBlueprint, diseaseDisplayName: string): string {
  const { mode } = blueprint;
  const cues = teachingCues(mode);
  const observations = composeObservations(blueprint);
  const lines = [
    `# Answer: ${mode} (${modeFullName(mode)})`,
    '',
    `**Disease in this puzzle:** ${diseaseDisplayName}`,
    '',
    '## Why this mode fits',
    '',
    ...cues.map((cue) => `- ${cue}`),
    '',
    '## What to look for in this particular pedigree',
    '',
    ...observations.map((line) => `- ${line}`),
    '',
    '## Teaching note',
    '',
    TEACHING_NOTES[mode],
    '',
  ];
  return lines.join('\n');
}

function composeObservations(blueprint: PedigreeBlueprint): readonly string[] {
  const affected = blueprint.individuals.filter((ind) => ind.affected);
  const generations = [...new Set(affected.map((ind) => ind.generation))].sort((a, b) => a - b);
  const males = affected.filter((ind) => ind.sex === 'male').length;
  const females = affected.length - males;
  const generationLabel = generations.length === 0 ? '[none]' : `[${generations.join(', ')}]`;
  return [
    `${String(affected.length)} affected individual(s) across generations ${generationLabel}.`,
    `Affected males: ${String(males)}; affected females: ${String(females)}.`,
    `The proband (${blueprint.probandId}) is the suggested index case.`,
  ];
}
