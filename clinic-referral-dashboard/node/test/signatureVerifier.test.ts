import { strictEqual } from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { test } from 'node:test';

import { verifySignature } from '../src/signatureVerifier.js';

const SECRET = 'shared-secret';
const BODY = Buffer.from('{"event":"pedigree.created"}', 'utf8');

function validSignature(body: Buffer, secret: string): string {
  return createHmac('sha256', secret).update(body).digest('hex');
}

test('accepts a correctly signed body', () => {
  strictEqual(verifySignature(BODY, validSignature(BODY, SECRET), SECRET), true);
});

test('accepts the sha256= prefixed form Evagene actually emits', () => {
  strictEqual(
    verifySignature(BODY, `sha256=${validSignature(BODY, SECRET)}`, SECRET),
    true,
  );
});

test('rejects a signature that does not match the body (replay of a different body)', () => {
  const tampered = Buffer.from('{"event":"pedigree.deleted"}', 'utf8');
  strictEqual(verifySignature(tampered, validSignature(BODY, SECRET), SECRET), false);
});

test('rejects a signature computed under a different secret', () => {
  strictEqual(verifySignature(BODY, validSignature(BODY, 'other-secret'), SECRET), false);
});

test('rejects when no signature header is present', () => {
  strictEqual(verifySignature(BODY, undefined, SECRET), false);
});

test('rejects a non-hex signature header', () => {
  strictEqual(verifySignature(BODY, 'sha256=nothex!!!', SECRET), false);
});

test('rejects a signature of the wrong length without throwing', () => {
  strictEqual(verifySignature(BODY, 'sha256=deadbeef', SECRET), false);
});
