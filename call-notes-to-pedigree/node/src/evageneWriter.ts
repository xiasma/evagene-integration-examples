/**
 * Persist an {@link ExtractedFamily} via the {@link EvageneApi}.
 * Orders calls so every `relative_of` points at an already-created individual:
 * pedigree, proband, parents, grandparents per side, siblings.
 */

import type { AddRelativeArgs, EvageneApi, RelativeType } from './evageneClient.js';
import {
  type ExtractedFamily,
  type RelativeEntry,
  type SiblingEntry,
  siblingBiologicalSex,
} from './extractedFamily.js';

export interface WriteResult {
  readonly pedigreeId: string;
  readonly probandId: string;
  readonly relativesAdded: number;
}

export class EvageneWriter {
  constructor(private readonly client: EvageneApi) {}

  async write(family: ExtractedFamily): Promise<WriteResult> {
    const pedigreeId = await this.client.createPedigree(
      `${family.proband.displayName}'s family`,
    );
    const probandId = await this.client.createIndividual({
      displayName: family.proband.displayName,
      biologicalSex: family.proband.biologicalSex,
      ...(family.proband.yearOfBirth !== undefined
        ? { yearOfBirth: family.proband.yearOfBirth }
        : {}),
    });
    await this.client.addIndividualToPedigree(pedigreeId, probandId);
    await this.client.designateAsProband(probandId);

    const motherId = await this.maybeAddRelative(
      pedigreeId,
      probandId,
      'mother',
      'female',
      family.mother,
    );
    const fatherId = await this.maybeAddRelative(
      pedigreeId,
      probandId,
      'father',
      'male',
      family.father,
    );

    let relativesAdded = countAdded(motherId, fatherId);
    if (motherId !== undefined) {
      relativesAdded += await this.addGrandparents(
        pedigreeId,
        motherId,
        family.maternalGrandmother,
        family.maternalGrandfather,
      );
    }
    if (fatherId !== undefined) {
      relativesAdded += await this.addGrandparents(
        pedigreeId,
        fatherId,
        family.paternalGrandmother,
        family.paternalGrandfather,
      );
    }
    relativesAdded += await this.addSiblings(pedigreeId, probandId, family.siblings);

    return { pedigreeId, probandId, relativesAdded };
  }

  private async addGrandparents(
    pedigreeId: string,
    parentId: string,
    grandmother: RelativeEntry | undefined,
    grandfather: RelativeEntry | undefined,
  ): Promise<number> {
    const gmId = await this.maybeAddRelative(
      pedigreeId,
      parentId,
      'mother',
      'female',
      grandmother,
    );
    const gfId = await this.maybeAddRelative(
      pedigreeId,
      parentId,
      'father',
      'male',
      grandfather,
    );
    return countAdded(gmId, gfId);
  }

  private async addSiblings(
    pedigreeId: string,
    probandId: string,
    siblings: readonly SiblingEntry[],
  ): Promise<number> {
    let added = 0;
    for (const sibling of siblings) {
      const args: AddRelativeArgs = {
        pedigreeId,
        relativeOf: probandId,
        relativeType: sibling.relation,
        displayName: sibling.displayName,
        biologicalSex: siblingBiologicalSex(sibling.relation),
        ...(sibling.yearOfBirth !== undefined ? { yearOfBirth: sibling.yearOfBirth } : {}),
      };
      await this.client.addRelative(args);
      added += 1;
    }
    return added;
  }

  private async maybeAddRelative(
    pedigreeId: string,
    relativeOf: string,
    relativeType: RelativeType,
    biologicalSex: 'female' | 'male',
    entry: RelativeEntry | undefined,
  ): Promise<string | undefined> {
    if (entry === undefined) {
      return undefined;
    }
    return this.client.addRelative({
      pedigreeId,
      relativeOf,
      relativeType,
      displayName: entry.displayName,
      biologicalSex,
      ...(entry.yearOfBirth !== undefined ? { yearOfBirth: entry.yearOfBirth } : {}),
    });
  }
}

function countAdded(...ids: (string | undefined)[]): number {
  return ids.filter(id => id !== undefined).length;
}
