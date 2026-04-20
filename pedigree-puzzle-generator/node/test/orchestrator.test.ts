import { deepStrictEqual, ok, strictEqual } from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';

import type {
  AddRelativeArgs,
  CreateIndividualArgs,
  DiseaseSummary,
  EvageneApi,
} from '../src/evageneClient.js';
import { PuzzleOrchestrator } from '../src/orchestrator.js';
import { buildBlueprint } from '../src/puzzleBlueprint.js';

class FakeClient implements EvageneApi {
  createdPedigrees: string[] = [];
  deletedPedigrees: string[] = [];
  probandIds: string[] = [];
  addRelativeCalls: AddRelativeArgs[] = [];
  diseasesAdded: [string, string][] = [];
  createdIndividuals: CreateIndividualArgs[] = [];
  svgFetches: string[] = [];
  private counter = 0;

  searchDiseases(nameFragment: string): Promise<DiseaseSummary> {
    return Promise.resolve({ diseaseId: 'disease-1', displayName: `Disease matching '${nameFragment}'` });
  }
  createPedigree(displayName: string): Promise<string> {
    this.createdPedigrees.push(displayName);
    return Promise.resolve('pedigree-uuid');
  }
  createIndividual(args: CreateIndividualArgs): Promise<string> {
    this.createdIndividuals.push(args);
    return Promise.resolve(this.nextId());
  }
  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<void> {
    void pedigreeId;
    void individualId;
    return Promise.resolve();
  }
  designateAsProband(individualId: string): Promise<void> {
    this.probandIds.push(individualId);
    return Promise.resolve();
  }
  addRelative(args: AddRelativeArgs): Promise<string> {
    this.addRelativeCalls.push(args);
    return Promise.resolve(this.nextId());
  }
  addDiseaseToIndividual(individualId: string, diseaseId: string): Promise<void> {
    this.diseasesAdded.push([individualId, diseaseId]);
    return Promise.resolve();
  }
  getPedigreeSvg(pedigreeId: string): Promise<string> {
    this.svgFetches.push(pedigreeId);
    return Promise.resolve('<svg/>');
  }
  deletePedigree(pedigreeId: string): Promise<void> {
    this.deletedPedigrees.push(pedigreeId);
    return Promise.resolve();
  }

  protected nextId(): string {
    this.counter += 1;
    return `remote-${String(this.counter)}`;
  }
}

const fixedClock = { now: (): Date => new Date(Date.UTC(2026, 3, 20, 14, 30, 12)) };
const silentLogger = {
  info(_message: string): void {
    void _message;
  },
  warn(_message: string): void {
    void _message;
  },
};

function makeOrchestrator(client: EvageneApi): PuzzleOrchestrator {
  return new PuzzleOrchestrator({
    client,
    clock: fixedClock,
    evageneBaseUrl: 'https://evagene.net',
    logger: silentLogger,
  });
}

async function withTempDir(fn: (dir: string) => Promise<void>): Promise<void> {
  const dir = await mkdtemp(path.join(tmpdir(), 'puzzle-orch-'));
  try {
    await fn(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

test('orchestrator writes question and answer files', async () => {
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AR', generations: 3, size: 'small', seed: 1 });
    const client = new FakeClient();

    const result = await makeOrchestrator(client).generate({
      blueprint,
      diseaseName: 'Cystic Fibrosis',
      outputDir: tmp,
      cleanup: true,
    });

    const answer = await readFile(result.artefact.answerPath, 'utf-8');
    ok(answer.includes('AR'));
  });
});

test('orchestrator deletes pedigree when cleanup requested', async () => {
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'small', seed: 1 });
    const client = new FakeClient();

    const result = await makeOrchestrator(client).generate({
      blueprint,
      diseaseName: 'Huntington',
      outputDir: tmp,
      cleanup: true,
    });

    strictEqual(result.pedigreeWasDeleted, true);
    deepStrictEqual(client.deletedPedigrees, ['pedigree-uuid']);
  });
});

test('orchestrator keeps pedigree when cleanup disabled', async () => {
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'small', seed: 1 });
    const client = new FakeClient();

    const result = await makeOrchestrator(client).generate({
      blueprint,
      diseaseName: 'Huntington',
      outputDir: tmp,
      cleanup: false,
    });

    strictEqual(result.pedigreeWasDeleted, false);
    deepStrictEqual(client.deletedPedigrees, []);
  });
});

test('orchestrator flags every affected individual with the disease', async () => {
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'small', seed: 1 });
    const client = new FakeClient();

    await makeOrchestrator(client).generate({
      blueprint,
      diseaseName: 'Huntington',
      outputDir: tmp,
      cleanup: true,
    });

    const expected = blueprint.individuals.filter((i) => i.affected).length;
    strictEqual(client.diseasesAdded.length, expected);
    for (const [, diseaseId] of client.diseasesAdded) {
      strictEqual(diseaseId, 'disease-1');
    }
  });
});

test('orchestrator deletes pedigree when mid-build fails', async () => {
  class ExplodingClient extends FakeClient {
    override addRelative(args: AddRelativeArgs): Promise<string> {
      void args;
      return Promise.reject(new Error('boom'));
    }
  }
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'small', seed: 1 });
    const client = new ExplodingClient();

    let caught: unknown;
    try {
      await makeOrchestrator(client).generate({
        blueprint,
        diseaseName: 'Huntington',
        outputDir: tmp,
        cleanup: true,
      });
    } catch (error) {
      caught = error;
    }
    ok(caught instanceof Error);
    deepStrictEqual(client.deletedPedigrees, ['pedigree-uuid']);
  });
});
