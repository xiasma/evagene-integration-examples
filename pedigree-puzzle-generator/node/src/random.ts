/**
 * Tiny seeded pseudo-random number generator.
 *
 * Uses the mulberry32 algorithm -- a compact, well-understood 32-bit
 * PRNG.  Sufficient for teaching puzzles; not for cryptography.  Keeps
 * the blueprint deterministic given a seed, which the test suite
 * relies on.
 */

export interface Rng {
  next(): number;
  int(lowInclusive: number, highInclusive: number): number;
  choice<T>(values: readonly T[]): T;
}

export function createRng(seed: number): Rng {
  let state = (seed >>> 0) || 1;
  const next = (): number => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    next,
    int(low, high) {
      return low + Math.floor(next() * (high - low + 1));
    },
    choice<T>(values: readonly T[]): T {
      if (values.length === 0) {
        throw new Error('cannot pick from an empty list');
      }
      const index = Math.floor(next() * values.length);
      const value = values[index];
      if (value === undefined) {
        throw new Error('random index out of bounds');
      }
      return value;
    },
  };
}
