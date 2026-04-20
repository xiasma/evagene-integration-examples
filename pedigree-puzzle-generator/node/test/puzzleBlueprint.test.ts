import { deepStrictEqual, notDeepStrictEqual, ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import { MODES, type Mode } from '../src/inheritance.js';
import {
  type BlueprintIndividual,
  type Generations,
  type PedigreeBlueprint,
  buildBlueprint,
} from '../src/puzzleBlueprint.js';

const FIXED_SEEDS: readonly number[] = [1, 42, 137, 2718, 9000];

test('blueprint is deterministic from seed', () => {
  for (const mode of MODES) {
    for (const seed of FIXED_SEEDS) {
      const first = buildBlueprint({ mode, generations: 3, size: 'medium', seed });
      const second = buildBlueprint({ mode, generations: 3, size: 'medium', seed });
      deepStrictEqual(first, second, `non-deterministic for ${mode} seed=${String(seed)}`);
    }
  }
});

test('different seeds give different blueprints', () => {
  const first = buildBlueprint({ mode: 'AD', generations: 3, size: 'medium', seed: 1 });
  const second = buildBlueprint({ mode: 'AD', generations: 3, size: 'medium', seed: 2 });
  notDeepStrictEqual(first, second);
});

test('every non-proband names an existing local id as relative', () => {
  for (const mode of MODES) {
    for (const seed of FIXED_SEEDS) {
      const blueprint = buildBlueprint({ mode, generations: 3, size: 'medium', seed });
      const known = new Set(blueprint.individuals.map((i) => i.localId));
      for (const ind of blueprint.individuals) {
        if (ind.buildKind === 'proband') continue;
        ok(ind.relativeType.length > 0, `${ind.localId} missing relativeType`);
        ok(
          known.has(ind.relativeOfLocalId),
          `${ind.localId} names unknown relative ${ind.relativeOfLocalId}`,
        );
      }
    }
  }
});

test('blueprint has exactly one proband', () => {
  const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'medium', seed: 1 });
  const probands = blueprint.individuals.filter((i) => i.buildKind === 'proband');
  strictEqual(probands.length, 1);
  strictEqual(probands[0]?.localId, blueprint.probandId);
});

test('AD mode has affected individuals across multiple generations', () => {
  for (const seed of FIXED_SEEDS) {
    const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'medium', seed });
    const generations = new Set(
      blueprint.individuals.filter((i) => i.affected).map((i) => i.generation),
    );
    ok(generations.size >= 2, `AD seed=${String(seed)} expected >=2 generations, got ${String(generations.size)}`);
  }
});

test('XLR mode only affects males', () => {
  for (const seed of FIXED_SEEDS) {
    const blueprint = buildBlueprint({ mode: 'XLR', generations: 3, size: 'medium', seed });
    const affectedFemales = blueprint.individuals.filter(
      (i) => i.affected && i.sex === 'female',
    );
    deepStrictEqual(affectedFemales, [], `XLR seed=${String(seed)} produced affected females`);
  }
});

test('MT mode: every affected non-proband child has an affected mother', () => {
  for (const seed of FIXED_SEEDS) {
    const blueprint = buildBlueprint({ mode: 'MT', generations: 3, size: 'medium', seed });
    for (const child of blueprint.individuals) {
      if (!child.affected || child.buildKind === 'proband') continue;
      const mother = motherOf(blueprint, child);
      if (mother !== null) {
        ok(
          mother.affected,
          `MT seed=${String(seed)}: ${child.localId} affected but mother ${mother.localId} not`,
        );
      }
    }
  }
});

test('AR mode: affected children trace to a carrier or affected parent on each side', () => {
  for (const seed of FIXED_SEEDS) {
    const blueprint = buildBlueprint({ mode: 'AR', generations: 3, size: 'medium', seed });
    for (const child of blueprint.individuals) {
      if (!child.affected) continue;
      const parents = parentsOf(blueprint, child);
      if (parents.length < 2) continue; // proband emitted first
      for (const parent of parents) {
        ok(
          parent.affected || parent.carrier,
          `AR seed=${String(seed)}: affected ${child.localId} has non-carrier parent ${parent.localId}`,
        );
      }
    }
  }
});

test('size small produces smaller pedigrees than large', () => {
  const small = buildBlueprint({ mode: 'AD', generations: 3, size: 'small', seed: 123 });
  const large = buildBlueprint({ mode: 'AD', generations: 3, size: 'large', seed: 123 });
  ok(small.individuals.length < large.individuals.length);
});

test('four generations produces more individuals than three', () => {
  const three = buildBlueprint({ mode: 'AD' as Mode, generations: 3 as Generations, size: 'medium', seed: 99 });
  const four = buildBlueprint({ mode: 'AD', generations: 4, size: 'medium', seed: 99 });
  ok(four.individuals.length > three.individuals.length);
});

test('blueprint order respects add-relative dependencies', () => {
  const blueprint = buildBlueprint({ mode: 'XLD', generations: 4, size: 'medium', seed: 55 });
  const seen = new Set<string>();
  for (const ind of blueprint.individuals) {
    if (ind.buildKind === 'proband') {
      seen.add(ind.localId);
      continue;
    }
    ok(
      seen.has(ind.relativeOfLocalId),
      `${ind.localId} emitted before its anchor ${ind.relativeOfLocalId}`,
    );
    seen.add(ind.localId);
  }
});

function motherOf(
  blueprint: PedigreeBlueprint,
  child: BlueprintIndividual,
): BlueprintIndividual | null {
  return (
    blueprint.individuals.find(
      (c) => c.relativeType === 'mother' && c.relativeOfLocalId === child.localId,
    ) ?? null
  );
}

function parentsOf(
  blueprint: PedigreeBlueprint,
  child: BlueprintIndividual,
): BlueprintIndividual[] {
  return blueprint.individuals.filter(
    (c) =>
      c.relativeOfLocalId === child.localId &&
      (c.relativeType === 'mother' || c.relativeType === 'father'),
  );
}
