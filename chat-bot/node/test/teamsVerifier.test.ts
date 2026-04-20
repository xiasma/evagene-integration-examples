import { strictEqual } from 'node:assert/strict';
import { createHmac, randomBytes } from 'node:crypto';
import { test } from 'node:test';

import { verifyTeamsRequest } from '../src/teamsVerifier.js';

const SECRET = randomBytes(32).toString('base64');
const BODY = Buffer.from('{"text":"@Evagene 7c8d4d6a-2f3a-4c1e-9a0b-5c2d3e4f5a6b"}', 'utf8');

function sign(body: Buffer, base64Key: string): string {
  const key = Buffer.from(base64Key, 'base64');
  const signature = createHmac('sha256', key).update(body).digest('base64');
  return `HMAC ${signature}`;
}

test('accepts a correctly signed body', () => {
  strictEqual(
    verifyTeamsRequest({
      rawBody: BODY,
      authorizationHeader: sign(BODY, SECRET),
      signingSecret: SECRET,
    }),
    true,
  );
});

test('rejects a signature computed under a different secret', () => {
  const otherSecret = randomBytes(32).toString('base64');
  strictEqual(
    verifyTeamsRequest({
      rawBody: BODY,
      authorizationHeader: sign(BODY, otherSecret),
      signingSecret: SECRET,
    }),
    false,
  );
});

test('rejects a tampered body', () => {
  strictEqual(
    verifyTeamsRequest({
      rawBody: Buffer.from('{"text":"evil"}', 'utf8'),
      authorizationHeader: sign(BODY, SECRET),
      signingSecret: SECRET,
    }),
    false,
  );
});

test('rejects a missing Authorization header', () => {
  strictEqual(
    verifyTeamsRequest({
      rawBody: BODY,
      authorizationHeader: undefined,
      signingSecret: SECRET,
    }),
    false,
  );
});

test('rejects an Authorization header without the HMAC prefix', () => {
  const signature = createHmac('sha256', Buffer.from(SECRET, 'base64'))
    .update(BODY)
    .digest('base64');
  strictEqual(
    verifyTeamsRequest({
      rawBody: BODY,
      authorizationHeader: `Bearer ${signature}`,
      signingSecret: SECRET,
    }),
    false,
  );
});

test('rejects a non-base64 signature payload', () => {
  strictEqual(
    verifyTeamsRequest({
      rawBody: BODY,
      authorizationHeader: 'HMAC not@base64!',
      signingSecret: SECRET,
    }),
    false,
  );
});

test('rejects a signature of the wrong byte length', () => {
  const shortSig = Buffer.alloc(16).toString('base64');
  strictEqual(
    verifyTeamsRequest({
      rawBody: BODY,
      authorizationHeader: `HMAC ${shortSig}`,
      signingSecret: SECRET,
    }),
    false,
  );
});

test('rejects when the signing secret itself is not base64', () => {
  strictEqual(
    verifyTeamsRequest({
      rawBody: BODY,
      authorizationHeader: sign(BODY, SECRET),
      signingSecret: 'not@base64!',
    }),
    false,
  );
});
