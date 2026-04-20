import { deepStrictEqual, ok, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type {
  CreateTemplateArgs,
  EvageneApi,
  RegisterData,
  Template,
} from '../src/evageneClient.js';
import { DEFAULT_TEMPLATE_NAME, resolveTemplateId } from '../src/templateResolver.js';

class FakeClient implements EvageneApi {
  readonly created: CreateTemplateArgs[] = [];
  private nextId = 100;

  constructor(public templates: Template[] = []) {}

  fetchRegister(pedigreeId: string): Promise<RegisterData> {
    throw new Error(`resolver should not fetch the register (asked for ${pedigreeId})`);
  }

  listTemplates(): Promise<readonly Template[]> {
    return Promise.resolve([...this.templates]);
  }

  createTemplate(args: CreateTemplateArgs): Promise<Template> {
    this.nextId += 1;
    const template: Template = { id: `auto-${this.nextId.toString()}`, name: args.name };
    this.templates.push(template);
    this.created.push(args);
    return Promise.resolve(template);
  }

  runTemplate(templateId: string, pedigreeId: string): Promise<string> {
    throw new Error(`resolver should not run template (${templateId}, ${pedigreeId})`);
  }
}

test('honours explicit override without calling the API', async () => {
  const client = new FakeClient([{ id: 'ignored', name: DEFAULT_TEMPLATE_NAME }]);

  const id = await resolveTemplateId(client, 'explicit-id');

  strictEqual(id, 'explicit-id');
  deepStrictEqual(client.created, []);
});

test('returns an existing template when found by name', async () => {
  const client = new FakeClient([
    { id: 'other', name: 'other' },
    { id: 'existing', name: DEFAULT_TEMPLATE_NAME },
  ]);

  const id = await resolveTemplateId(client, undefined);

  strictEqual(id, 'existing');
  deepStrictEqual(client.created, []);
});

test('creates a template when none matches the expected name', async () => {
  const client = new FakeClient([{ id: 'other', name: 'other' }]);

  const id = await resolveTemplateId(client, undefined);

  ok(id.startsWith('auto-'));
  strictEqual(client.created.length, 1);
  strictEqual(client.created[0]?.name, DEFAULT_TEMPLATE_NAME);
  ok(client.created[0]?.userPromptTemplate.includes('{{proband_name}}'));
  ok(client.created[0]?.userPromptTemplate.includes('{{disease_list}}'));
});

test('uses a caller-supplied template name', async () => {
  const client = new FakeClient();

  await resolveTemplateId(client, undefined, 'my-template');

  strictEqual(client.created[0]?.name, 'my-template');
});
