/**
 * Slack request-signing verification (v0 scheme).
 *
 *   base    = "v0:" + timestamp + ":" + raw_body
 *   sig_hex = HMAC_SHA256(signing_secret, base)
 *   header  = "v0=" + sig_hex
 *
 * Constant-time compare via `timingSafeEqual` and reject timestamps older
 * than five minutes to block replay attacks. Reference:
 *   https://api.slack.com/authentication/verifying-requests-from-slack
 */

import { createHmac, timingSafeEqual } from 'node:crypto';

const SIGNATURE_PREFIX = 'v0=';
const BASE_STRING_PREFIX = 'v0:';
const SHA256_HEX_LENGTH = 64;
const HEX_CHAR_RE = /^[0-9a-f]+$/i;
const REPLAY_WINDOW_SECONDS = 5 * 60;

export interface SlackVerificationInput {
  readonly rawBody: Buffer;
  readonly signatureHeader: string | undefined;
  readonly timestampHeader: string | undefined;
  readonly signingSecret: string;
  readonly nowSeconds: number;
}

export function verifySlackRequest(input: SlackVerificationInput): boolean {
  const timestamp = parseTimestamp(input.timestampHeader);
  if (timestamp === undefined) {
    return false;
  }
  if (Math.abs(input.nowSeconds - timestamp) > REPLAY_WINDOW_SECONDS) {
    return false;
  }
  const presented = parseSignatureHeader(input.signatureHeader);
  if (presented === undefined) {
    return false;
  }
  const base = Buffer.concat([
    Buffer.from(`${BASE_STRING_PREFIX}${timestamp.toString()}:`, 'utf8'),
    input.rawBody,
  ]);
  const expected = createHmac('sha256', input.signingSecret).update(base).digest();
  return presented.length === expected.length && timingSafeEqual(presented, expected);
}

function parseTimestamp(header: string | undefined): number | undefined {
  if (header === undefined) {
    return undefined;
  }
  const parsed = Number.parseInt(header, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function parseSignatureHeader(header: string | undefined): Buffer | undefined {
  if (!header?.startsWith(SIGNATURE_PREFIX)) {
    return undefined;
  }
  const hex = header.slice(SIGNATURE_PREFIX.length);
  if (hex.length !== SHA256_HEX_LENGTH || !HEX_CHAR_RE.test(hex)) {
    return undefined;
  }
  return Buffer.from(hex, 'hex');
}
