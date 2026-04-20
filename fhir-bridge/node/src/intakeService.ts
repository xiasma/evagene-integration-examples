/**
 * Orchestrates the REST calls that turn an IntakeFamily into a fresh
 * Evagene pedigree with a proband and all its relatives attached.
 *
 * No HTTP knowledge: the service only talks to the EvageneApi interface
 * so tests can drive it without a network.
 */

import type { EvageneApi } from './evageneClient.js';
import type { IntakeFamily } from './intakeFamily.js';

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

  async create(family: IntakeFamily): Promise<IntakeCreationResult> {
    const { client } = this.options;

    const pedigreeId = await client.createPedigree({
      displayName: family.pedigreeDisplayName,
    });
    const probandId = await this.createProband(family);
    await client.addIndividualToPedigree(pedigreeId, probandId);
    await client.designateAsProband(probandId);

    let added = 0;
    for (const relative of family.relatives) {
      await client.addRelative({
        pedigreeId,
        relativeOf: probandId,
        relativeType: relative.relativeType,
        displayName: relative.displayName,
        biologicalSex: relative.biologicalSex,
        ...(relative.yearOfBirth !== undefined ? { yearOfBirth: relative.yearOfBirth } : {}),
      });
      added += 1;
    }

    return { pedigreeId, probandId, relativesAdded: added };
  }

  private async createProband(family: IntakeFamily): Promise<string> {
    return this.options.client.createIndividual({
      displayName: family.proband.displayName,
      biologicalSex: family.proband.biologicalSex,
      ...(family.proband.yearOfBirth !== undefined
        ? { yearOfBirth: family.proband.yearOfBirth }
        : {}),
    });
  }
}
