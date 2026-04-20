/**
 * Compose a blueprint into a live pedigree and Markdown artefacts.
 *
 * No HTTP knowledge -- the orchestrator depends only on EvageneApi.
 * No Markdown formatting -- that belongs to writer and answerExplainer.
 */

import { explain } from './answerExplainer.js';
import type { EvageneApi } from './evageneClient.js';
import type {
  BlueprintIndividual,
  PedigreeBlueprint,
} from './puzzleBlueprint.js';
import type { PuzzleArtefact } from './writer.js';
import { writePuzzle } from './writer.js';

export interface Clock {
  now(): Date;
}

export interface Logger {
  info(message: string): void;
  warn(message: string): void;
}

export interface PuzzleResult {
  readonly artefact: PuzzleArtefact;
  readonly pedigreeId: string;
  readonly pedigreeWasDeleted: boolean;
}

export interface OrchestratorOptions {
  readonly client: EvageneApi;
  readonly clock: Clock;
  readonly evageneBaseUrl: string;
  readonly logger: Logger;
}

export interface GenerateArgs {
  readonly blueprint: PedigreeBlueprint;
  readonly diseaseName: string;
  readonly outputDir: string;
  readonly cleanup: boolean;
}

export class PuzzleOrchestrator {
  private readonly client: EvageneApi;
  private readonly clock: Clock;
  private readonly baseUrl: string;
  private readonly logger: Logger;

  constructor(options: OrchestratorOptions) {
    this.client = options.client;
    this.clock = options.clock;
    this.baseUrl = options.evageneBaseUrl;
    this.logger = options.logger;
  }

  async generate(args: GenerateArgs): Promise<PuzzleResult> {
    const disease = await this.client.searchDiseases(args.diseaseName);
    const pedigreeId = await this.client.createPedigree(
      `Puzzle: ${args.blueprint.mode} / ${disease.displayName}`,
    );
    this.logger.info(`Created scratch pedigree ${pedigreeId}`);

    let artefact: PuzzleArtefact;
    try {
      const idMap = await this.materialiseIndividuals(args.blueprint, pedigreeId);
      await this.markAffected(args.blueprint, idMap, disease.diseaseId);
      const svg = await this.client.getPedigreeSvg(pedigreeId);
      artefact = await writePuzzle({
        outputDir: args.outputDir,
        timestamp: this.clock.now(),
        blueprint: args.blueprint,
        diseaseDisplayName: disease.displayName,
        pedigreeId,
        evageneBaseUrl: this.baseUrl,
        svg,
        answerMarkdown: explain(args.blueprint, disease.displayName),
      });
    } catch (error) {
      await this.safelyDelete(pedigreeId, 'aborted mid-build');
      throw error;
    }

    let pedigreeWasDeleted = false;
    if (args.cleanup) {
      await this.client.deletePedigree(pedigreeId);
      pedigreeWasDeleted = true;
      this.logger.info(`Deleted scratch pedigree ${pedigreeId}`);
    }

    return { artefact, pedigreeId, pedigreeWasDeleted };
  }

  private async materialiseIndividuals(
    blueprint: PedigreeBlueprint,
    pedigreeId: string,
  ): Promise<Map<string, string>> {
    const idMap = new Map<string, string>();
    for (const individual of blueprint.individuals) {
      const remoteId = await this.createIndividual(individual, pedigreeId, idMap);
      idMap.set(individual.localId, remoteId);
    }
    const probandRemote = idMap.get(blueprint.probandId);
    if (probandRemote === undefined) {
      throw new Error('Proband was not materialised on the remote pedigree.');
    }
    await this.client.designateAsProband(probandRemote);
    return idMap;
  }

  private async createIndividual(
    individual: BlueprintIndividual,
    pedigreeId: string,
    idMap: Map<string, string>,
  ): Promise<string> {
    if (individual.buildKind === 'proband') {
      const remote = await this.client.createIndividual({
        displayName: individual.displayName,
        sex: individual.sex,
      });
      await this.client.addIndividualToPedigree(pedigreeId, remote);
      return remote;
    }
    const anchor = idMap.get(individual.relativeOfLocalId);
    if (anchor === undefined) {
      throw new Error(
        `Relative ${individual.localId} references unknown anchor ${individual.relativeOfLocalId}`,
      );
    }
    return this.client.addRelative({
      pedigreeId,
      relativeOf: anchor,
      relativeType: individual.relativeType,
      displayName: individual.displayName,
      sex: individual.sex,
    });
  }

  private async markAffected(
    blueprint: PedigreeBlueprint,
    idMap: Map<string, string>,
    diseaseId: string,
  ): Promise<void> {
    for (const individual of blueprint.individuals) {
      if (!individual.affected) continue;
      const remote = idMap.get(individual.localId);
      if (remote === undefined) continue;
      await this.client.addDiseaseToIndividual(remote, diseaseId);
    }
  }

  private async safelyDelete(pedigreeId: string, reason: string): Promise<void> {
    try {
      await this.client.deletePedigree(pedigreeId);
      this.logger.info(`Deleted scratch pedigree ${pedigreeId} (${reason})`);
    } catch {
      this.logger.warn(
        `Failed to delete scratch pedigree ${pedigreeId} after ${reason}; clean up manually.`,
      );
    }
  }
}
