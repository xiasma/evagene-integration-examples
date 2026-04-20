import { strictEqual } from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { test } from 'node:test';

import { verifySlackRequest } from '../src/slackVerifier.js';

const SECRET = 'slack-signing-secret';
const NOW = 1_713_614_400;
const BODY = Buffer.from('token=t&text=7c8d4d6a-2f3a-4c1e-9a0b-5c2d3e4f5a6b', 'utf8');

function sign(timestamp: number, body: Buffer, secret: string): string {
  const base = Buffer.concat([Buffer.from(`v0:${timestamp.toString()}:`, 'utf8'), body]);
  const hex = createHmac('sha256', secret).update(base).digest('hex');
  return `v0=${hex}`;
}

test('accepts a correctly signed, fresh request', () => {
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: sign(NOW, BODY, SECRET),
      timestampHeader: NOW.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    true,
  );
});

test('rejects a signature computed under a different secret', () => {
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: sign(NOW, BODY, 'other-secret'),
      timestampHeader: NOW.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});

test('rejects a timestamp older than five minutes', () => {
  const stale = NOW - 6 * 60;
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: sign(stale, BODY, SECRET),
      timestampHeader: stale.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});

test('rejects a timestamp too far in the future', () => {
  const future = NOW + 6 * 60;
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: sign(future, BODY, SECRET),
      timestampHeader: future.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});

test('rejects a missing signature header', () => {
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: undefined,
      timestampHeader: NOW.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});

test('rejects a missing timestamp header', () => {
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: sign(NOW, BODY, SECRET),
      timestampHeader: undefined,
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});

test('rejects a non-hex signature of the wrong length', () => {
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: 'v0=nothex!!!',
      timestampHeader: NOW.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});

test('rejects a signature with missing v0 prefix', () => {
  const hex = createHmac('sha256', SECRET)
    .update(Buffer.concat([Buffer.from(`v0:${NOW.toString()}:`, 'utf8'), BODY]))
    .digest('hex');
  strictEqual(
    verifySlackRequest({
      rawBody: BODY,
      signatureHeader: hex,
      timestampHeader: NOW.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});

test('rejects a tampered body even with matching timestamp + header', () => {
  strictEqual(
    verifySlackRequest({
      rawBody: Buffer.from('token=t&text=other', 'utf8'),
      signatureHeader: sign(NOW, BODY, SECRET),
      timestampHeader: NOW.toString(),
      signingSecret: SECRET,
      nowSeconds: NOW,
    }),
    false,
  );
});
