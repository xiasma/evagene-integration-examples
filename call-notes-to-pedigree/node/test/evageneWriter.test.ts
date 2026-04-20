import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type {
  AddRelativeArgs,
  CreateIndividualArgs,
} from '../src/evageneClient.js';
import { EvageneWriter } from '../src/evageneWriter.js';
import type { ExtractedFamily } from '../src/extractedFamily.js';

interface Call {
  readonly op: string;
  readonly payload: unknown;
}

class RecordingClient {
  calls: Call[] = [];
  private nextId = 1;

  private issueId(): string {
    const id = `id-${this.nextId.toString().padStart(4, '0')}`;
    this.nextId += 1;
    return id;
  }

  createPedigree(displayName: string): Promise<string> {
    const id = this.issueId();
    this.calls.push({ op: 'createPedigree', payload: { displayName, returned: id } });
    return Promise.resolve(id);
  }

  createIndividual(args: CreateIndividualArgs): Promise<string> {
    const id = this.issueId();
    this.calls.push({ op: 'createIndividual', payload: { ...args, returned: id } });
    return Promise.resolve(id);
  }

  addIndividualToPedigree(pedigreeId: string, individualId: string): Promise<void> {
    this.calls.push({ op: 'addIndividualToPedigree', payload: { pedigreeId, individualId } });
    return Promise.resolve();
  }

  designateAsProband(individualId: string): Promise<void> {
    this.calls.push({ op: 'designateAsProband', payload: { individualId } });
    return Promise.resolve();
  }

  addRelative(args: AddRelativeArgs): Promise<string> {
    const id = this.issueId();
    this.calls.push({ op: 'addRelative', payload: { ...args, returned: id } });
    return Promise.resolve(id);
  }
}

function family(overrides: Partial<ExtractedFamily> = {}): ExtractedFamily {
  return {
    proband: { displayName: 'Emma', biologicalSex: 'female' },
    siblings: [],
    ...overrides,
  };
}

test('proband-only family runs setup then stops', async () => {
  const client = new RecordingClient();
  const result = await new EvageneWriter(client).write(family());

  deepStrictEqual(
    client.calls.map(call => call.op),
    ['createPedigree', 'createIndividual', 'addIndividualToPedigree', 'designateAsProband'],
  );
  strictEqual(result.relativesAdded, 0);
});

test('parents are added before their grandparents', async () => {
  const client = new RecordingClient();

  await new EvageneWriter(client).write(
    family({
      mother: { displayName: 'Grace' },
      father: { displayName: 'Henry' },
      maternalGrandmother: { displayName: 'Edith' },
      paternalGrandfather: { displayName: 'Arthur' },
    }),
  );

  const relatives = client.calls
    .filter(call => call.op === 'addRelative')
    .map(call => {
      const args = call.payload as AddRelativeArgs;
      return { type: args.relativeType, name: args.displayName };
    });
  deepStrictEqual(relatives, [
    { type: 'mother', name: 'Grace' },
    { type: 'father', name: 'Henry' },
    { type: 'mother', name: 'Edith' },
    { type: 'father', name: 'Arthur' },
  ]);
});

test('grandparent on a side with no parent is skipped', async () => {
  const client = new RecordingClient();

  await new EvageneWriter(client).write(
    family({ maternalGrandmother: { displayName: 'Edith' } }),
  );

  strictEqual(client.calls.filter(call => call.op === 'addRelative').length, 0);
});

test('sibling sex is derived from relation', async () => {
  const client = new RecordingClient();

  await new EvageneWriter(client).write(
    family({
      siblings: [
        { displayName: 'Alice', relation: 'sister' },
        { displayName: 'Ben', relation: 'half_brother' },
      ],
    }),
  );

  const siblingCalls = client.calls.filter(call => call.op === 'addRelative');
  const alice = siblingCalls[0]?.payload as AddRelativeArgs;
  const ben = siblingCalls[1]?.payload as AddRelativeArgs;
  strictEqual(alice.biologicalSex, 'female');
  strictEqual(alice.relativeType, 'sister');
  strictEqual(ben.biologicalSex, 'male');
  strictEqual(ben.relativeType, 'half_brother');
});
