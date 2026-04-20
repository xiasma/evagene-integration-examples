/**
 * Pure pedigree builder: a mode + shape + seed yield a deterministic blueprint.
 *
 * Genotypes are decided top-down so the mode's signature is visible at
 * the root of the tree; the blueprint is then emitted in dependency
 * order for the add-relative REST surface, which works bottom-up
 * (proband exists first, then mother, then father; the server merges
 * mother + father into the same egg).
 *
 * "Pure" here is load-bearing for the test suite: fixtures lock in the
 * expected blueprint for a handful of seeds per mode, and anything
 * that reaches for Math.random() at module scope would make those
 * tests flaky.  All randomness flows through the injected Rng.
 */

import type { Mode, Sex } from './inheritance.js';
import { type OffspringGenotype, offspringAffectedProbability } from './modeHeuristics.js';
import { type Rng, createRng } from './random.js';

export type Generations = 3 | 4;
export type Size = 'small' | 'medium' | 'large';
export type BuildKind = 'proband' | 'relative';

export interface BlueprintIndividual {
  readonly localId: string;
  readonly displayName: string;
  readonly sex: Sex;
  readonly affected: boolean;
  readonly carrier: boolean;
  readonly generation: number;
  readonly buildKind: BuildKind;
  readonly relativeType: string;
  readonly relativeOfLocalId: string;
}

export interface PedigreeBlueprint {
  readonly individuals: readonly BlueprintIndividual[];
  readonly probandId: string;
  readonly mode: Mode;
}

export function findIndividual(
  blueprint: PedigreeBlueprint,
  localId: string,
): BlueprintIndividual {
  const match = blueprint.individuals.find((ind) => ind.localId === localId);
  if (match === undefined) {
    throw new Error(`Unknown blueprint individual: ${localId}`);
  }
  return match;
}

const SIZE_RANGE: Readonly<Record<Size, readonly [number, number]>> = {
  small: [2, 3],
  medium: [3, 5],
  large: [5, 7],
};

const EVEN_SEX_RATIO = 0.5;

export function buildBlueprint(options: {
  readonly mode: Mode;
  readonly generations: Generations;
  readonly size: Size;
  readonly seed: number;
}): PedigreeBlueprint {
  const rng = createRng(options.seed);
  const plan = planTree(options.mode, options.generations, options.size, rng);
  return emitBlueprint(plan, options.mode);
}

// ---------------------------------------------------------------------------
// Phase 1 -- plan the tree top-down so genotypes inherit correctly.
// ---------------------------------------------------------------------------

interface PlannedPerson {
  readonly key: string;
  readonly sex: Sex;
  readonly affected: boolean;
  readonly carrier: boolean;
  readonly generation: number;
}

interface PlannedFamily {
  readonly mother: PlannedPerson;
  readonly father: PlannedPerson;
  readonly children: readonly PlannedPerson[];
  nextFamily: PlannedFamily | null;
  reproducingChildKey: string;
}

interface Plan {
  readonly root: PlannedFamily;
  readonly probandKey: string;
}

class KeyGen {
  private n = 0;
  next(): string {
    this.n += 1;
    return `K${String(this.n).padStart(3, '0')}`;
  }
}

function planTree(
  mode: Mode,
  generations: Generations,
  size: Size,
  rng: Rng,
): Plan {
  const keys = new KeyGen();
  const [rootMother, rootFather] = topFounders(mode, keys);
  const root = planFamily({ mode, size, rng, keys, mother: rootMother, father: rootFather, childGeneration: 2 });

  let current: PlannedFamily = root;
  for (let generation = 2; generation < generations; generation += 1) {
    const reproducing = pickReproducingChild(mode, current.children, rng);
    current.reproducingChildKey = reproducing.key;
    const spouse = marriedInSpouse(mode, reproducing, keys);
    const mother = reproducing.sex === 'female' ? reproducing : spouse;
    const father = reproducing.sex === 'male' ? reproducing : spouse;
    const nextFamily = planFamily({
      mode,
      size,
      rng,
      keys,
      mother,
      father,
      childGeneration: generation + 1,
    });
    current.nextFamily = nextFamily;
    current = nextFamily;
  }

  const proband = pickProband(current.children);
  return { root, probandKey: proband.key };
}

function topFounders(mode: Mode, keys: KeyGen): readonly [PlannedPerson, PlannedPerson] {
  const [motherAffected, motherCarrier] = topFounderStatus(mode, 'female');
  const [fatherAffected, fatherCarrier] = topFounderStatus(mode, 'male');
  const mother: PlannedPerson = {
    key: keys.next(),
    sex: 'female',
    affected: motherAffected,
    carrier: motherCarrier,
    generation: 1,
  };
  const father: PlannedPerson = {
    key: keys.next(),
    sex: 'male',
    affected: fatherAffected,
    carrier: fatherCarrier,
    generation: 1,
  };
  return [mother, father];
}

function marriedInSpouse(mode: Mode, reproducing: PlannedPerson, keys: KeyGen): PlannedPerson {
  // For teaching AR, the married-in spouse is a silent carrier so that
  // downstream generations can produce an affected proband.
  const carrier = mode === 'AR';
  return {
    key: keys.next(),
    sex: reproducing.sex === 'female' ? 'male' : 'female',
    affected: false,
    carrier,
    generation: reproducing.generation,
  };
}

function planFamily(args: {
  readonly mode: Mode;
  readonly size: Size;
  readonly rng: Rng;
  readonly keys: KeyGen;
  readonly mother: PlannedPerson;
  readonly father: PlannedPerson;
  readonly childGeneration: number;
}): PlannedFamily {
  const { mode, size, rng, keys, mother, father, childGeneration } = args;
  const genotype: OffspringGenotype = {
    motherAffected: mother.affected,
    motherCarrier: mother.carrier,
    fatherAffected: father.affected,
    fatherCarrier: father.carrier,
  };
  const [low, high] = SIZE_RANGE[size];
  const childCount = rng.int(low, high);
  const children: PlannedPerson[] = [];
  for (let i = 0; i < childCount; i += 1) {
    const sex: Sex = rng.next() < EVEN_SEX_RATIO ? 'female' : 'male';
    const affected = rng.next() < offspringAffectedProbability(mode, genotype, sex);
    const carrier = isObligateCarrier(mode, sex, genotype, affected);
    children.push({
      key: keys.next(),
      sex,
      affected,
      carrier,
      generation: childGeneration,
    });
  }
  return { mother, father, children, nextFamily: null, reproducingChildKey: '' };
}

function pickReproducingChild(
  mode: Mode,
  children: readonly PlannedPerson[],
  rng: Rng,
): PlannedPerson {
  const preferred = preferredLineCarriers(mode, children);
  const pool = preferred.length > 0 ? preferred : children;
  return rng.choice(pool);
}

function preferredLineCarriers(
  mode: Mode,
  children: readonly PlannedPerson[],
): readonly PlannedPerson[] {
  switch (mode) {
    case 'MT':
      return children.filter((c) => c.sex === 'female');
    case 'XLR':
    case 'XLD':
      return children.filter((c) => c.sex === 'female' && (c.affected || c.carrier));
    case 'AD':
      return children.filter((c) => c.affected);
    case 'AR':
      return children.filter((c) => c.affected || c.carrier);
  }
}

function pickProband(children: readonly PlannedPerson[]): PlannedPerson {
  const affected = children.filter((c) => c.affected);
  if (affected.length > 0) {
    const first = affected[0];
    if (first !== undefined) return first;
  }
  const head = children[0];
  if (head === undefined) {
    throw new Error('bottom-generation family has no children');
  }
  return head;
}

// ---------------------------------------------------------------------------
// Phase 2 -- emit build steps in dependency order for add-relative.
// ---------------------------------------------------------------------------

function emitBlueprint(plan: Plan, mode: Mode): PedigreeBlueprint {
  const emitter = new Emitter();
  const proband = findPlannedPerson(plan.root, plan.probandKey);
  emitter.emitProband(proband);

  let anchorKey = plan.probandKey;
  let anchorFamily: PlannedFamily | null = findFamilyOf(plan.root, plan.probandKey);

  while (anchorFamily !== null) {
    const anchorLocal = emitter.localIdOf(anchorKey);
    emitter.emitRelative(anchorFamily.mother, 'mother', anchorLocal);
    emitter.emitRelative(anchorFamily.father, 'father', anchorLocal);
    for (const sibling of anchorFamily.children) {
      if (sibling.key === anchorKey) continue;
      if (sibling.key === anchorFamily.reproducingChildKey) continue;
      const relativeType = sibling.sex === 'female' ? 'sister' : 'brother';
      emitter.emitRelative(sibling, relativeType, anchorLocal);
    }
    const parentFamily = parentFamilyOf(plan.root, anchorFamily);
    if (parentFamily === null) break;
    anchorKey = parentFamily.reproducingChildKey;
    anchorFamily = parentFamily;
  }

  return {
    individuals: emitter.individuals,
    probandId: emitter.localIdOf(plan.probandKey),
    mode,
  };
}

class Emitter {
  readonly individuals: BlueprintIndividual[] = [];
  private readonly byKey = new Map<string, string>();
  private nextIndex = 0;

  emitProband(person: PlannedPerson): string {
    return this.record(person, 'proband', '', '');
  }

  emitRelative(person: PlannedPerson, relativeType: string, relativeOfLocalId: string): string {
    const existing = this.byKey.get(person.key);
    if (existing !== undefined) return existing;
    return this.record(person, 'relative', relativeType, relativeOfLocalId);
  }

  localIdOf(key: string): string {
    const value = this.byKey.get(key);
    if (value === undefined) {
      throw new Error(`No local id emitted yet for ${key}`);
    }
    return value;
  }

  private record(
    person: PlannedPerson,
    buildKind: BuildKind,
    relativeType: string,
    relativeOfLocalId: string,
  ): string {
    this.nextIndex += 1;
    const localId = `I${String(this.nextIndex).padStart(3, '0')}`;
    this.individuals.push({
      localId,
      displayName: `Person ${String(this.nextIndex)}`,
      sex: person.sex,
      affected: person.affected,
      carrier: person.carrier,
      generation: person.generation,
      buildKind,
      relativeType,
      relativeOfLocalId,
    });
    this.byKey.set(person.key, localId);
    return localId;
  }
}

function findPlannedPerson(root: PlannedFamily, key: string): PlannedPerson {
  let family: PlannedFamily | null = root;
  while (family !== null) {
    if (family.mother.key === key) return family.mother;
    if (family.father.key === key) return family.father;
    for (const child of family.children) {
      if (child.key === key) return child;
    }
    family = family.nextFamily;
  }
  throw new Error(`Planned person not found: ${key}`);
}

function findFamilyOf(root: PlannedFamily, childKey: string): PlannedFamily | null {
  let family: PlannedFamily | null = root;
  while (family !== null) {
    for (const child of family.children) {
      if (child.key === childKey) return family;
    }
    family = family.nextFamily;
  }
  return null;
}

function parentFamilyOf(root: PlannedFamily, family: PlannedFamily): PlannedFamily | null {
  if (family === root) return null;
  let current: PlannedFamily | null = root;
  while (current !== null) {
    if (current.nextFamily === family) return current;
    current = current.nextFamily;
  }
  return null;
}

function topFounderStatus(mode: Mode, sex: Sex): readonly [boolean, boolean] {
  if (mode === 'AD') return [sex === 'female', false];
  if (mode === 'AR') return [false, true];
  if (mode === 'XLR') return [false, sex === 'female'];
  if (mode === 'XLD') {
    return sex === 'female' ? [false, false] : [true, false];
  }
  // MT
  return [sex === 'female', false];
}

function isObligateCarrier(
  mode: Mode,
  childSex: Sex,
  parents: OffspringGenotype,
  affected: boolean,
): boolean {
  if (affected) return false;
  if (
    mode === 'AR' &&
    (parents.motherAffected || parents.motherCarrier) &&
    (parents.fatherAffected || parents.fatherCarrier)
  ) {
    return true;
  }
  return (
    mode === 'XLR' &&
    childSex === 'female' &&
    (parents.motherCarrier || parents.motherAffected || parents.fatherAffected)
  );
}
