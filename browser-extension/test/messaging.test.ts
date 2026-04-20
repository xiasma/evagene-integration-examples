import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { test } from 'node:test';

import type { HandlerMap, LookupRequest, Response } from '../src/messaging.js';
import { failure, route } from '../src/messaging.js';

function okResponse(id: string): Response {
  return {
    kind: 'lookup-result',
    ok: true,
    summary: {
      pedigreeId: id,
      name: 'Example pedigree',
      probandName: 'Alice',
      diseases: ['Breast cancer'],
      viewUrl: `https://evagene.example/pedigrees/${id}`,
    },
  };
}

function handlers(onLookup: (message: LookupRequest) => Response): HandlerMap {
  return {
    'lookup-pedigree': message => Promise.resolve(onLookup(message)),
  };
}

test('routes lookup-pedigree to the lookup handler', async () => {
  const seen: LookupRequest[] = [];
  const response = await route(
    { kind: 'lookup-pedigree', pedigreeId: 'abc' },
    handlers(message => {
      seen.push(message);
      return okResponse(message.pedigreeId);
    }),
  );

  deepStrictEqual(seen, [{ kind: 'lookup-pedigree', pedigreeId: 'abc' }]);
  strictEqual(response.kind, 'lookup-result');
  strictEqual(response.ok, true);
});

test('returns failure for unknown envelopes', async () => {
  const response = await route(
    { kind: 'not-a-thing' },
    handlers(() => okResponse('unused')),
  );
  deepStrictEqual(response, failure('Unknown message envelope'));
});

test('returns failure for non-object inputs', async () => {
  const response = await route('hello', handlers(() => okResponse('unused')));
  strictEqual(response.ok, false);
});
