import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type {
  AddRelativeArgs,
  CreateIndividualArgs,
  CreatePedigreeArgs,
} from '../src/evageneClient.js';
import { IntakeService } from '../src/intakeService.js';
import type { IntakeSubmission } from '../src/intakeSubmission.js';

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

  createPedigree(args: CreatePedigreeArgs): Promise<string> {
    const id = this.issueId();
    this.calls.push({ op: 'createPedigree', payload: { ...args, returned: id } });
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

function submission(overrides: Partial<IntakeSubmission> = {}): IntakeSubmission {
  return {
    proband: { displayName: 'Emma', biologicalSex: 'female' },
    siblings: [],
    ...overrides,
  };
}

function opsOf(client: RecordingClient): string[] {
  return client.calls.map(call => call.op);
}

test('proband-only submission creates pedigree, individual, adds, designates', async () => {
  const client = new RecordingClient();
  const service = new IntakeService({ client });

  const result = await service.create(submission());

  deepStrictEqual(opsOf(client), [
    'createPedigree',
    'createIndividual',
    'addIndividualToPedigree',
    'designateAsProband',
  ]);
  strictEqual(result.relativesAdded, 0);
  strictEqual(result.pedigreeId, 'id-0001');
  strictEqual(result.probandId, 'id-0002');
});

test('mother and father are added before their respective grandparents', async () => {
  const client = new RecordingClient();
  const service = new IntakeService({ client });

  await service.create(
    submission({
      mother: { displayName: 'Grace' },
      father: { displayName: 'Henry' },
      maternalGrandmother: { displayName: 'Edith' },
      paternalGrandfather: { displayName: 'Arthur' },
    }),
  );

  const addRelativeCalls = client.calls.filter(call => call.op === 'addRelative');
  const relatives = addRelativeCalls.map(call => {
    const args = call.payload as AddRelativeArgs & { readonly returned: string };
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
  const service = new IntakeService({ client });

  await service.create(
    submission({
      maternalGrandmother: { displayName: 'Edith' },
    }),
  );

  const relativesAdded = client.calls.filter(call => call.op === 'addRelative').length;
  strictEqual(relativesAdded, 0);
});

test('siblings come last and carry biological sex derived from relation', async () => {
  const client = new RecordingClient();
  const service = new IntakeService({ client });

  const result = await service.create(
    submission({
      siblings: [
        { displayName: 'Alice', relation: 'sister', biologicalSex: 'female' },
        { displayName: 'Bob', relation: 'brother', biologicalSex: 'male' },
      ],
    }),
  );

  const siblingCalls = client.calls.filter(call => {
    const payload = call.payload as { readonly relativeType?: string };
    return payload.relativeType === 'sister' || payload.relativeType === 'brother';
  });
  strictEqual(siblingCalls.length, 2);
  strictEqual(result.relativesAdded, 2);
});

test('relativesAdded counts every successful add-relative call', async () => {
  const client = new RecordingClient();
  const service = new IntakeService({ client });

  const result = await service.create(
    submission({
      mother: { displayName: 'Grace' },
      father: { displayName: 'Henry' },
      maternalGrandmother: { displayName: 'Edith' },
      maternalGrandfather: { displayName: 'Cecil' },
      paternalGrandmother: { displayName: 'Margaret' },
      paternalGrandfather: { displayName: 'Arthur' },
      siblings: [{ displayName: 'Alice', relation: 'sister', biologicalSex: 'female' }],
    }),
  );

  strictEqual(result.relativesAdded, 7);
});
