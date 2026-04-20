/**
 * Teaching heuristics for each inheritance mode, as pure data.
 *
 * Two callers use this module: puzzleBlueprint reads
 * offspringAffectedProbability to decide whether each simulated child
 * inherits the trait, and answerExplainer reads the teaching cues so
 * the answer sheet stays aligned with the same rules.  Keeping both
 * consumers pointed at one definition prevents drift between "how we
 * built the puzzle" and "how we explain the answer".
 */

import type { Mode, Sex } from './inheritance.js';

export interface OffspringGenotype {
  readonly motherAffected: boolean;
  readonly motherCarrier: boolean;
  readonly fatherAffected: boolean;
  readonly fatherCarrier: boolean;
}

type Rule = (parents: OffspringGenotype, childSex: Sex) => number;

const ad: Rule = (parents) => {
  if (parents.motherAffected && parents.fatherAffected) return 1.0;
  if (parents.motherAffected || parents.fatherAffected) return 0.5;
  return 0.0;
};

const ar: Rule = (parents) => {
  const motherHasAllele = parents.motherAffected || parents.motherCarrier;
  const fatherHasAllele = parents.fatherAffected || parents.fatherCarrier;
  if (!(motherHasAllele && fatherHasAllele)) return 0.0;
  const motherTransmits = parents.motherAffected ? 1.0 : 0.5;
  const fatherTransmits = parents.fatherAffected ? 1.0 : 0.5;
  return motherTransmits * fatherTransmits;
};

const xlr: Rule = (parents, childSex) => {
  if (childSex === 'male') {
    if (parents.motherAffected) return 1.0;
    if (parents.motherCarrier) return 0.5;
    return 0.0;
  }
  if (parents.fatherAffected && (parents.motherAffected || parents.motherCarrier)) {
    return parents.motherCarrier ? 0.5 : 1.0;
  }
  return 0.0;
};

const xld: Rule = (parents, childSex) => {
  if (childSex === 'female') {
    if (parents.fatherAffected) return 1.0;
    if (parents.motherAffected) return 0.5;
    return 0.0;
  }
  if (parents.motherAffected) return 0.5;
  return 0.0;
};

const mt: Rule = (parents) => (parents.motherAffected ? 1.0 : 0.0);

const RULE_BY_MODE: Readonly<Record<Mode, Rule>> = { AD: ad, AR: ar, XLR: xlr, XLD: xld, MT: mt };

export function offspringAffectedProbability(
  mode: Mode,
  parents: OffspringGenotype,
  childSex: Sex,
): number {
  return RULE_BY_MODE[mode](parents, childSex);
}

const TEACHING_CUES: Readonly<Record<Mode, readonly string[]>> = {
  AD: [
    'Affected individuals in every generation (vertical transmission).',
    'Both sexes affected roughly equally.',
    'Male-to-male transmission is possible, ruling out X-linked.',
    'Each child of an affected parent has a ~50% risk.',
  ],
  AR: [
    'Affected individuals often appear in only one generation (horizontal clustering among siblings).',
    'Both parents of an affected child are typically unaffected obligate carriers.',
    'Both sexes affected equally.',
    'Consanguinity, where shown, raises the prior probability.',
  ],
  XLR: [
    'Almost only males are affected.',
    'Transmitted through unaffected female carriers (skipped generations on the female line).',
    'No male-to-male transmission -- affected fathers never pass it to sons.',
    'All daughters of an affected father are obligate carriers.',
  ],
  XLD: [
    'Both sexes affected, but females typically outnumber males (two X chromosomes).',
    'Every daughter of an affected father is affected; no sons of an affected father are affected.',
    'No male-to-male transmission.',
    'Affected mothers pass it to ~50% of children of either sex.',
  ],
  MT: [
    'Transmitted exclusively through the mother (matrilineal).',
    'Affected fathers never transmit to any child.',
    'Affected mothers transmit to all children, though expression can vary with heteroplasmy.',
    'Both sexes affected.',
  ],
};

export function teachingCues(mode: Mode): readonly string[] {
  return TEACHING_CUES[mode];
}
