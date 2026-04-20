/**
 * Microsoft Teams outgoing-webhook HMAC verification.
 *
 *   sig_bytes = HMAC_SHA256(key_bytes, raw_body_bytes)
 *   header    = "HMAC " + base64(sig_bytes)
 *
 * The signing key is the base64 token Teams returns when the outgoing
 * webhook is created; decode it before using it as the HMAC key.
 * Reference:
 *   https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-outgoing-webhook
 */

import { createHmac, timingSafeEqual } from 'node:crypto';

const AUTH_PREFIX = 'HMAC ';
const SHA256_BYTE_LENGTH = 32;
const BASE64_CHAR_RE = /^[A-Za-z0-9+/]+={0,2}$/;

export interface TeamsVerificationInput {
  readonly rawBody: Buffer;
  readonly authorizationHeader: string | undefined;
  readonly signingSecret: string;
}

export function verifyTeamsRequest(input: TeamsVerificationInput): boolean {
  const presented = parseSignatureHeader(input.authorizationHeader);
  if (presented === undefined) {
    return false;
  }
  const key = parseBase64(input.signingSecret);
  if (key === undefined) {
    return false;
  }
  const expected = createHmac('sha256', key).update(input.rawBody).digest();
  return presented.length === expected.length && timingSafeEqual(presented, expected);
}

function parseSignatureHeader(header: string | undefined): Buffer | undefined {
  if (!header?.startsWith(AUTH_PREFIX)) {
    return undefined;
  }
  const encoded = header.slice(AUTH_PREFIX.length).trim();
  const bytes = parseBase64(encoded);
  return bytes !== undefined && bytes.length === SHA256_BYTE_LENGTH ? bytes : undefined;
}

function parseBase64(value: string): Buffer | undefined {
  if (value === '' || !BASE64_CHAR_RE.test(value)) {
    return undefined;
  }
  const buffer = Buffer.from(value, 'base64');
  if (buffer.length === 0) {
    return undefined;
  }
  // Round-trip check: Buffer.from silently discards invalid trailing bytes.
  if (buffer.toString('base64').replace(/=+$/, '') !== value.replace(/=+$/, '')) {
    return undefined;
  }
  return buffer;
}
