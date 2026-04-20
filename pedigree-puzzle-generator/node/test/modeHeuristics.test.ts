import { ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { MODES } from '../src/inheritance.js';
import {
  type OffspringGenotype,
  offspringAffectedProbability,
  teachingCues,
} from '../src/modeHeuristics.js';

const carrierMotherUnaffectedFather: OffspringGenotype = {
  motherAffected: false,
  motherCarrier: true,
  fatherAffected: false,
  fatherCarrier: false,
};

const bothCarriers: OffspringGenotype = {
  motherAffected: false,
  motherCarrier: true,
  fatherAffected: false,
  fatherCarrier: true,
};

const affectedMother: OffspringGenotype = {
  motherAffected: true,
  motherCarrier: false,
  fatherAffected: false,
  fatherCarrier: false,
};

const affectedFather: OffspringGenotype = {
  motherAffected: false,
  motherCarrier: false,
  fatherAffected: true,
  fatherCarrier: false,
};

test('AD: affected parent gives 50% risk', () => {
  strictEqual(offspringAffectedProbability('AD', affectedMother, 'male'), 0.5);
  strictEqual(offspringAffectedProbability('AD', affectedFather, 'female'), 0.5);
});

test('AD: two unaffected parents give zero risk', () => {
  const unaffected: OffspringGenotype = {
    motherAffected: false,
    motherCarrier: false,
    fatherAffected: false,
    fatherCarrier: false,
  };
  strictEqual(offspringAffectedProbability('AD', unaffected, 'male'), 0.0);
});

test('AR: both carriers gives 25% risk', () => {
  strictEqual(offspringAffectedProbability('AR', bothCarriers, 'male'), 0.25);
});

test('AR: only one carrier parent gives zero risk', () => {
  strictEqual(offspringAffectedProbability('AR', carrierMotherUnaffectedFather, 'male'), 0.0);
});

test('XLR: carrier mother affects 50% of sons and no daughters', () => {
  strictEqual(offspringAffectedProbability('XLR', carrierMotherUnaffectedFather, 'male'), 0.5);
  strictEqual(offspringAffectedProbability('XLR', carrierMotherUnaffectedFather, 'female'), 0.0);
});

test('XLD: affected father affects all daughters, no sons', () => {
  strictEqual(offspringAffectedProbability('XLD', affectedFather, 'female'), 1.0);
  strictEqual(offspringAffectedProbability('XLD', affectedFather, 'male'), 0.0);
});

test('MT: affected mother affects every child', () => {
  strictEqual(offspringAffectedProbability('MT', affectedMother, 'male'), 1.0);
  strictEqual(offspringAffectedProbability('MT', affectedMother, 'female'), 1.0);
});

test('MT: affected father affects no child', () => {
  strictEqual(offspringAffectedProbability('MT', affectedFather, 'male'), 0.0);
  strictEqual(offspringAffectedProbability('MT', affectedFather, 'female'), 0.0);
});

test('teaching cues are non-empty for every mode', () => {
  for (const mode of MODES) {
    const cues = teachingCues(mode);
    ok(cues.length > 0, `no teaching cues for ${mode}`);
    for (const cue of cues) {
      ok(cue.trim().length > 0, `empty teaching cue in ${mode}`);
    }
  }
});

test('XLR teaching cues mention male-to-male rule', () => {
  const joined = teachingCues('XLR').join(' ').toLowerCase();
  ok(joined.includes('male-to-male'));
});
