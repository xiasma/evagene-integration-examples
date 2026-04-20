/**
 * Walks a PedigreeDetail and labels every other individual with their
 * relation to the proband.
 *
 * Evagene models a family as individuals + couple relationships + eggs
 * (child belongs to a couple). From the proband's eggs we find parents;
 * from parents' eggs we find grandparents; siblings share parents;
 * children come through eggs where the proband is on the couple; and so
 * on for aunts, uncles, nieces, nephews, and cousins.
 *
 * Pure function: input in, map out, no I/O.
 */

import type { PedigreeDetail, PedigreeIndividual } from './pedigreeDetail.js';
import type { RelativeType } from './intakeFamily.js';

export interface RelationView {
  readonly individual: PedigreeIndividual;
  readonly relativeType: RelativeType;
}

export interface ProbandRelationsResult {
  readonly proband: PedigreeIndividual;
  readonly relatives: readonly RelationView[];
  readonly unlabelled: readonly PedigreeIndividual[];
}

export function relationsFromProband(detail: PedigreeDetail): ProbandRelationsResult | undefined {
  const proband = detail.individuals.find(i => i.proband);
  if (proband === undefined) {
    return undefined;
  }

  const graph = buildGraph(detail);
  const labels = new Map<string, RelativeType>();

  labelParents(proband.id, graph, labels, 'mother', 'father');
  labelMaternalGrandparents(proband.id, graph, labels);
  labelPaternalGrandparents(proband.id, graph, labels);
  labelSiblings(proband.id, graph, labels);
  labelChildren(proband.id, graph, labels);
  labelAuntsAndUncles(proband.id, graph, labels);
  labelNiecesAndNephews(graph, labels);
  labelFirstCousins(graph, labels);

  const relatives: RelationView[] = [];
  const unlabelled: PedigreeIndividual[] = [];
  for (const individual of detail.individuals) {
    if (individual.id === proband.id) {
      continue;
    }
    const label = labels.get(individual.id);
    if (label === undefined) {
      unlabelled.push(individual);
    } else {
      relatives.push({ individual, relativeType: label });
    }
  }

  return { proband, relatives, unlabelled };
}

interface Graph {
  readonly individualsById: ReadonlyMap<string, PedigreeIndividual>;
  /** individual id -> couple relationship ids they sit on (as a partner) */
  readonly couplesByPartner: ReadonlyMap<string, readonly string[]>;
  /** couple relationship id -> partner individual ids */
  readonly partnersByCouple: ReadonlyMap<string, readonly string[]>;
  /** couple relationship id -> child individual ids (via eggs) */
  readonly childrenByCouple: ReadonlyMap<string, readonly string[]>;
  /** individual id -> couple relationship id that they are a child of */
  readonly parentCoupleOfChild: ReadonlyMap<string, string>;
}

function buildGraph(detail: PedigreeDetail): Graph {
  const individualsById = new Map(detail.individuals.map(i => [i.id, i]));
  const couplesByPartner = new Map<string, string[]>();
  const partnersByCouple = new Map<string, string[]>();
  for (const relationship of detail.relationships) {
    partnersByCouple.set(relationship.id, [...relationship.members]);
    for (const partner of relationship.members) {
      const existing = couplesByPartner.get(partner) ?? [];
      existing.push(relationship.id);
      couplesByPartner.set(partner, existing);
    }
  }
  const childrenByCouple = new Map<string, string[]>();
  const parentCoupleOfChild = new Map<string, string>();
  for (const egg of detail.eggs) {
    const siblings = childrenByCouple.get(egg.relationshipId) ?? [];
    siblings.push(egg.individualId);
    childrenByCouple.set(egg.relationshipId, siblings);
    parentCoupleOfChild.set(egg.individualId, egg.relationshipId);
  }
  return {
    individualsById,
    couplesByPartner,
    partnersByCouple,
    childrenByCouple,
    parentCoupleOfChild,
  };
}

function parentsOf(individualId: string, graph: Graph): { mother?: string; father?: string } {
  const coupleId = graph.parentCoupleOfChild.get(individualId);
  if (coupleId === undefined) {
    return {};
  }
  const partners = graph.partnersByCouple.get(coupleId) ?? [];
  const result: { mother?: string; father?: string } = {};
  for (const partnerId of partners) {
    const partner = graph.individualsById.get(partnerId);
    if (partner === undefined) {
      continue;
    }
    if (partner.biologicalSex === 'female' && result.mother === undefined) {
      result.mother = partnerId;
    } else if (partner.biologicalSex === 'male' && result.father === undefined) {
      result.father = partnerId;
    }
  }
  return result;
}

function labelParents(
  probandId: string,
  graph: Graph,
  labels: Map<string, RelativeType>,
  motherLabel: RelativeType,
  fatherLabel: RelativeType,
): void {
  const { mother, father } = parentsOf(probandId, graph);
  if (mother !== undefined) {
    labels.set(mother, motherLabel);
  }
  if (father !== undefined) {
    labels.set(father, fatherLabel);
  }
}

function labelMaternalGrandparents(
  probandId: string,
  graph: Graph,
  labels: Map<string, RelativeType>,
): void {
  const { mother } = parentsOf(probandId, graph);
  if (mother === undefined) {
    return;
  }
  const { mother: mgm, father: mgf } = parentsOf(mother, graph);
  if (mgm !== undefined) {
    labels.set(mgm, 'maternal_grandmother');
  }
  if (mgf !== undefined) {
    labels.set(mgf, 'maternal_grandfather');
  }
}

function labelPaternalGrandparents(
  probandId: string,
  graph: Graph,
  labels: Map<string, RelativeType>,
): void {
  const { father } = parentsOf(probandId, graph);
  if (father === undefined) {
    return;
  }
  const { mother: pgm, father: pgf } = parentsOf(father, graph);
  if (pgm !== undefined) {
    labels.set(pgm, 'paternal_grandmother');
  }
  if (pgf !== undefined) {
    labels.set(pgf, 'paternal_grandfather');
  }
}

function labelSiblings(
  probandId: string,
  graph: Graph,
  labels: Map<string, RelativeType>,
): void {
  const parents = parentsOf(probandId, graph);
  if (parents.mother === undefined && parents.father === undefined) {
    return;
  }
  const coupleId = graph.parentCoupleOfChild.get(probandId);
  if (coupleId === undefined) {
    return;
  }
  const fullSiblings = new Set(graph.childrenByCouple.get(coupleId) ?? []);
  for (const siblingId of fullSiblings) {
    if (siblingId === probandId || labels.has(siblingId)) {
      continue;
    }
    const sibling = graph.individualsById.get(siblingId);
    if (sibling === undefined) {
      continue;
    }
    labels.set(siblingId, sibling.biologicalSex === 'male' ? 'brother' : 'sister');
  }

  const halfLabelFor = (sex: 'male' | 'female' | 'unknown'): RelativeType =>
    sex === 'male' ? 'half_brother' : 'half_sister';
  for (const [parent, label] of [
    [parents.mother, halfLabelFor],
    [parents.father, halfLabelFor],
  ] as const) {
    if (parent === undefined) {
      continue;
    }
    const otherCoupleIds = (graph.couplesByPartner.get(parent) ?? []).filter(id => id !== coupleId);
    for (const otherCoupleId of otherCoupleIds) {
      for (const halfId of graph.childrenByCouple.get(otherCoupleId) ?? []) {
        if (halfId === probandId || labels.has(halfId)) {
          continue;
        }
        const half = graph.individualsById.get(halfId);
        if (half === undefined) {
          continue;
        }
        labels.set(halfId, label(half.biologicalSex));
      }
    }
  }
}

function labelChildren(
  probandId: string,
  graph: Graph,
  labels: Map<string, RelativeType>,
): void {
  for (const coupleId of graph.couplesByPartner.get(probandId) ?? []) {
    for (const childId of graph.childrenByCouple.get(coupleId) ?? []) {
      if (labels.has(childId)) {
        continue;
      }
      const child = graph.individualsById.get(childId);
      if (child === undefined) {
        continue;
      }
      labels.set(childId, child.biologicalSex === 'male' ? 'son' : 'daughter');
    }
  }
}

function labelAuntsAndUncles(
  probandId: string,
  graph: Graph,
  labels: Map<string, RelativeType>,
): void {
  const parents = parentsOf(probandId, graph);
  if (parents.mother !== undefined) {
    labelSideAuntsUncles(parents.mother, graph, labels, 'maternal_aunt', 'maternal_uncle');
  }
  if (parents.father !== undefined) {
    labelSideAuntsUncles(parents.father, graph, labels, 'paternal_aunt', 'paternal_uncle');
  }
}

function labelSideAuntsUncles(
  parentId: string,
  graph: Graph,
  labels: Map<string, RelativeType>,
  auntLabel: RelativeType,
  uncleLabel: RelativeType,
): void {
  const parentCoupleId = graph.parentCoupleOfChild.get(parentId);
  if (parentCoupleId === undefined) {
    return;
  }
  for (const siblingId of graph.childrenByCouple.get(parentCoupleId) ?? []) {
    if (siblingId === parentId || labels.has(siblingId)) {
      continue;
    }
    const sibling = graph.individualsById.get(siblingId);
    if (sibling === undefined) {
      continue;
    }
    labels.set(siblingId, sibling.biologicalSex === 'male' ? uncleLabel : auntLabel);
  }
}

function labelNiecesAndNephews(
  graph: Graph,
  labels: Map<string, RelativeType>,
): void {
  for (const [id, label] of Array.from(labels.entries())) {
    if (label !== 'brother' && label !== 'sister' && label !== 'half_brother' && label !== 'half_sister') {
      continue;
    }
    for (const coupleId of graph.couplesByPartner.get(id) ?? []) {
      for (const childId of graph.childrenByCouple.get(coupleId) ?? []) {
        if (labels.has(childId)) {
          continue;
        }
        const child = graph.individualsById.get(childId);
        if (child === undefined) {
          continue;
        }
        labels.set(childId, child.biologicalSex === 'male' ? 'nephew' : 'niece');
      }
    }
  }
}

function labelFirstCousins(
  graph: Graph,
  labels: Map<string, RelativeType>,
): void {
  for (const [id, label] of Array.from(labels.entries())) {
    if (
      label !== 'maternal_aunt' &&
      label !== 'maternal_uncle' &&
      label !== 'paternal_aunt' &&
      label !== 'paternal_uncle'
    ) {
      continue;
    }
    for (const coupleId of graph.couplesByPartner.get(id) ?? []) {
      for (const childId of graph.childrenByCouple.get(coupleId) ?? []) {
        if (labels.has(childId)) {
          continue;
        }
        labels.set(childId, 'first_cousin');
      }
    }
  }
}
