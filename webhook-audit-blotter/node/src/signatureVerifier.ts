/**
 * HMAC-SHA256 signature check for an Evagene webhook delivery.
 *
 * The comparison uses `timingSafeEqual` to avoid leaking the secret via
 * wall-clock timing differences between a matching and a mismatching byte.
 * Never compare signatures with `===`.
 */

import { createHmac, timingSafeEqual } from 'node:crypto';

const HEX_PREFIX = 'sha256=';
const SHA256_HEX_LENGTH = 64;
const HEX_CHAR_RE = /^[0-9a-f]+$/i;

export function verifySignature(
  rawBody: Buffer,
  signatureHeader: string | undefined,
  secret: string,
): boolean {
  const presented = parseSignatureHeader(signatureHeader);
  if (presented === undefined) {
    return false;
  }
  const expected = createHmac('sha256', secret).update(rawBody).digest();
  return presented.length === expected.length && timingSafeEqual(presented, expected);
}

function parseSignatureHeader(header: string | undefined): Buffer | undefined {
  if (header === undefined) {
    return undefined;
  }
  const stripped = header.startsWith(HEX_PREFIX) ? header.slice(HEX_PREFIX.length) : header;
  if (stripped.length !== SHA256_HEX_LENGTH || !HEX_CHAR_RE.test(stripped)) {
    return undefined;
  }
  return Buffer.from(stripped, 'hex');
}
