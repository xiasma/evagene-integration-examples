/**
 * Orchestrates the sequence of Evagene REST calls that turn a validated
 * IntakeSubmission into a persisted pedigree with relatives wired up.
 *
 * No HTTP knowledge -- only the EvageneClient interface.  The order of
 * calls is load-bearing: grandparents depend on parents existing first
 * (the `relative_of` field points at an already-created individual).
 */

import type { EvageneApi, RelativeType } from './evageneClient.js';
import type {
  IntakeSubmission,
  RelativeEntry,
  SiblingEntry,
} from './intakeSubmission.js';

export interface IntakeServiceOptions {
  readonly client: EvageneApi;
}

export interface IntakeCreationResult {
  readonly pedigreeId: string;
  readonly probandId: string;
  readonly relativesAdded: number;
}

export class IntakeService {
  constructor(private readonly options: IntakeServiceOptions) {}

  async create(submission: IntakeSubmission): Promise<IntakeCreationResult> {
    const { client } = this.options;

    const pedigreeId = await client.createPedigree({
      displayName: `${submission.proband.displayName}'s family`,
    });
    const probandId = await client.createIndividual({
      displayName: submission.proband.displayName,
      biologicalSex: submission.proband.biologicalSex,
      ...(submission.proband.yearOfBirth !== undefined
        ? { yearOfBirth: submission.proband.yearOfBirth }
        : {}),
    });
    await client.addIndividualToPedigree(pedigreeId, probandId);
    await client.designateAsProband(probandId);

    const motherId = await this.maybeAddRelative(
      pedigreeId,
      probandId,
      'mother',
      'female',
      submission.mother,
    );
    const fatherId = await this.maybeAddRelative(
      pedigreeId,
      probandId,
      'father',
      'male',
      submission.father,
    );

    let relativesAdded = countAdded(motherId, fatherId);

    if (motherId !== undefined) {
      relativesAdded += await this.addGrandparents(
        pedigreeId,
        motherId,
        submission.maternalGrandmother,
        submission.maternalGrandfather,
        'maternal',
      );
    }
    if (fatherId !== undefined) {
      relativesAdded += await this.addGrandparents(
        pedigreeId,
        fatherId,
        submission.paternalGrandmother,
        submission.paternalGrandfather,
        'paternal',
      );
    }
    relativesAdded += await this.addSiblings(pedigreeId, probandId, submission.siblings);

    return { pedigreeId, probandId, relativesAdded };
  }

  private async addGrandparents(
    pedigreeId: string,
    parentId: string,
    grandmother: RelativeEntry | undefined,
    grandfather: RelativeEntry | undefined,
    side: 'maternal' | 'paternal',
  ): Promise<number> {
    const grandmotherId = await this.maybeAddRelative(
      pedigreeId,
      parentId,
      'mother',
      'female',
      grandmother,
    );
    const grandfatherId = await this.maybeAddRelative(
      pedigreeId,
      parentId,
      'father',
      'male',
      grandfather,
    );
    // side is carried only for future disambiguation / logging hooks.
    void side;
    return countAdded(grandmotherId, grandfatherId);
  }

  private async addSiblings(
    pedigreeId: string,
    probandId: string,
    siblings: readonly SiblingEntry[],
  ): Promise<number> {
    let added = 0;
    for (const sibling of siblings) {
      await this.options.client.addRelative({
        pedigreeId,
        relativeOf: probandId,
        relativeType: sibling.relation,
        displayName: sibling.displayName,
        biologicalSex: sibling.biologicalSex,
        ...(sibling.yearOfBirth !== undefined ? { yearOfBirth: sibling.yearOfBirth } : {}),
      });
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
    return this.options.client.addRelative({
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
