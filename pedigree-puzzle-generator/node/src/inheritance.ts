/**
 * Inheritance-mode enum and the associated biological-sex enum.
 *
 * Kept separate from puzzleBlueprint so the pure domain vocabulary
 * has nothing to do with pedigree-building mechanics -- answerExplainer
 * and modeHeuristics both depend on this, but not on each other.
 */

export const MODES = ['AD', 'AR', 'XLR', 'XLD', 'MT'] as const;
export type Mode = (typeof MODES)[number];

export type Sex = 'female' | 'male';

const FULL_NAMES: Readonly<Record<Mode, string>> = {
  AD: 'Autosomal Dominant',
  AR: 'Autosomal Recessive',
  XLR: 'X-linked Recessive',
  XLD: 'X-linked Dominant',
  MT: 'Mitochondrial',
};

export function modeFullName(mode: Mode): string {
  return FULL_NAMES[mode];
}
