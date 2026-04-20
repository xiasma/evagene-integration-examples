import { deepStrictEqual, rejects, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import {
  CascadeService,
  NoAtRiskRelativesError,
  type CascadeRequest,
} from '../src/cascadeService.js';
import type {
  CreateTemplateArgs,
  EvageneApi,
  RegisterData,
  Template,
} from '../src/evageneClient.js';
import type { LetterFile, LetterSink } from '../src/letterWriter.js';

const PROBAND_ID = 'a0000000-0000-0000-0000-000000000001';
const SISTER_ID = 'a0000000-0000-0000-0000-000000000002';
const PEDIGREE_ID = 'f0000000-0000-0000-0000-000000000000';

function brcaRegister(): RegisterData {
  return {
    probandId: PROBAND_ID,
    rows: [
      {
        individualId: PROBAND_ID,
        displayName: 'Helen Ward',
        relationshipToProband: 'Proband',
      },
      {
        individualId: SISTER_ID,
        displayName: 'Sarah Ward',
        relationshipToProband: 'Sister',
      },
    ],
  };
}

class FakeClient implements EvageneApi {
  readonly runCalls: [string, string][] = [];
  readonly templates: Template[] = [];

  constructor(
    private readonly register: RegisterData,
    private readonly renderedBody = 'Template body.\n',
  ) {}

  fetchRegister(pedigreeId: string): Promise<RegisterData> {
    strictEqual(typeof pedigreeId, 'string');
    return Promise.resolve(this.register);
  }

  listTemplates(): Promise<readonly Template[]> {
    return Promise.resolve([...this.templates]);
  }

  createTemplate(args: CreateTemplateArgs): Promise<Template> {
    const template: Template = { id: 'auto-created', name: args.name };
    this.templates.push(template);
    return Promise.resolve(template);
  }

  runTemplate(templateId: string, pedigreeId: string): Promise<string> {
    this.runCalls.push([templateId, pedigreeId]);
    return Promise.resolve(this.renderedBody);
  }
}

class RecordingSink implements LetterSink {
  readonly letters: LetterFile[] = [];

  write(letter: LetterFile): string {
    this.letters.push(letter);
    return `memory://${letter.filename}`;
  }
}

function request(overrides: Partial<CascadeRequest>): CascadeRequest {
  return { pedigreeId: PEDIGREE_ID, dryRun: false, ...overrides };
}

test('dry-run lists targets and skips run + write', async () => {
  const client = new FakeClient(brcaRegister());
  const sink = new RecordingSink();

  const result = await new CascadeService({ client, sink }).generateLetters(
    request({ dryRun: true }),
  );

  deepStrictEqual(
    result.targets.map(t => t.displayName),
    ['Sarah Ward'],
  );
  deepStrictEqual(result.writtenPaths, []);
  deepStrictEqual(client.runCalls, []);
  deepStrictEqual(sink.letters, []);
});

test('full run writes one letter per at-risk relative', async () => {
  const client = new FakeClient(brcaRegister());
  const sink = new RecordingSink();

  const result = await new CascadeService({ client, sink }).generateLetters(
    request({ templateOverride: 'override-id' }),
  );

  strictEqual(sink.letters.length, 1);
  strictEqual(sink.letters[0]?.filename, '01-sarah-ward.md');
  strictEqual(sink.letters[0]?.content.includes('Sarah Ward'), true);
  strictEqual(sink.letters[0]?.content.includes('Template body.'), true);
  deepStrictEqual(result.writtenPaths, ['memory://01-sarah-ward.md']);
  deepStrictEqual(client.runCalls, [['override-id', PEDIGREE_ID]]);
});

test('without override, service uses or creates a template', async () => {
  const client = new FakeClient(brcaRegister());
  const sink = new RecordingSink();

  await new CascadeService({ client, sink }).generateLetters(request({}));

  strictEqual(client.runCalls[0]?.[0], 'auto-created');
});

test('register with no proband raises NoAtRiskRelativesError', async () => {
  const client = new FakeClient({ probandId: null, rows: [] });
  const sink = new RecordingSink();

  await rejects(
    () => new CascadeService({ client, sink }).generateLetters(request({})),
    NoAtRiskRelativesError,
  );
});

test('register without at-risk relatives raises NoAtRiskRelativesError', async () => {
  const register: RegisterData = {
    probandId: PROBAND_ID,
    rows: [
      {
        individualId: PROBAND_ID,
        displayName: 'Helen Ward',
        relationshipToProband: 'Proband',
      },
    ],
  };
  const client = new FakeClient(register);
  const sink = new RecordingSink();

  await rejects(
    () => new CascadeService({ client, sink }).generateLetters(request({})),
    NoAtRiskRelativesError,
  );
});
