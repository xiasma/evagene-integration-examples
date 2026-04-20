import { ok, strictEqual } from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';

import { buildBlueprint } from '../src/puzzleBlueprint.js';
import { writePuzzle } from '../src/writer.js';

async function withTempDir(fn: (dir: string) => Promise<void>): Promise<void> {
  const dir = await mkdtemp(path.join(tmpdir(), 'puzzle-writer-'));
  try {
    await fn(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

test('writePuzzle creates a timestamped folder with three files', async () => {
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AR', generations: 3, size: 'medium', seed: 42 });
    const timestamp = new Date(Date.UTC(2026, 3, 20, 14, 30, 12));

    const artefact = await writePuzzle({
      outputDir: tmp,
      timestamp,
      blueprint,
      diseaseDisplayName: 'Cystic Fibrosis',
      pedigreeId: '7c8d4d6a-0000-0000-0000-000000000000',
      evageneBaseUrl: 'https://evagene.net',
      svg: '<svg>...</svg>',
      answerMarkdown: '# Answer: AR\nsample',
    });

    strictEqual(artefact.folder, path.join(tmp, 'puzzle-20260420-143012'));
    ok(artefact.questionPath.endsWith('question.md'));
    ok(artefact.answerPath.endsWith('answer.md'));
    const svg = await readFile(path.join(artefact.folder, 'pedigree.svg'), 'utf-8');
    strictEqual(svg, '<svg>...</svg>');
  });
});

test('question markdown links to the pedigree on Evagene and includes the SVG', async () => {
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AR', generations: 3, size: 'medium', seed: 42 });
    const timestamp = new Date(Date.UTC(2026, 3, 20, 14, 30, 12));

    const artefact = await writePuzzle({
      outputDir: tmp,
      timestamp,
      blueprint,
      diseaseDisplayName: 'Cystic Fibrosis',
      pedigreeId: '7c8d4d6a-0000-0000-0000-000000000000',
      evageneBaseUrl: 'https://evagene.net',
      svg: '<svg/>',
      answerMarkdown: '# Answer: AR\n',
    });

    const question = await readFile(artefact.questionPath, 'utf-8');
    ok(question.includes('https://evagene.net/pedigrees/7c8d4d6a-0000-0000-0000-000000000000'));
    ok(question.includes('![Pedigree](pedigree.svg)'));
  });
});

test('answer markdown is written verbatim', async () => {
  await withTempDir(async (tmp) => {
    const blueprint = buildBlueprint({ mode: 'AD', generations: 3, size: 'medium', seed: 1 });
    const timestamp = new Date(Date.UTC(2026, 0, 1, 0, 0, 0));

    const artefact = await writePuzzle({
      outputDir: tmp,
      timestamp,
      blueprint,
      diseaseDisplayName: "Huntington's Disease",
      pedigreeId: '00000000-0000-0000-0000-000000000000',
      evageneBaseUrl: 'https://evagene.net',
      svg: '<svg>hi</svg>',
      answerMarkdown: '# Answer: AD\nbody',
    });

    const answer = await readFile(artefact.answerPath, 'utf-8');
    strictEqual(answer, '# Answer: AD\nbody');
  });
});
