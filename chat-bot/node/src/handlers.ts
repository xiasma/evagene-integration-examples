/**
 * Framework-agnostic orchestration: signature check, pedigree-ID parse,
 * Evagene calls, per-platform render. Server adapters just call into this.
 */

import { EvageneApiError, type EvageneApi, type NiceResult, type PedigreeSummary } from './evageneClient.js';
import { verifySlackRequest } from './slackVerifier.js';
import { verifyTeamsRequest } from './teamsVerifier.js';
import { renderSlack, renderSlackError, type SlackResponse } from './renderSlack.js';
import { renderTeams, renderTeamsError, type TeamsResponse } from './renderTeams.js';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface Clock {
  nowSeconds(): number;
}

export interface ChatLinks {
  readonly webUrl: string;
  readonly svgUrl: string;
}

export interface ChatReport {
  readonly summary: PedigreeSummary;
  readonly nice: NiceResult;
  readonly links: ChatLinks;
}

export interface SlackDelivery {
  readonly rawBody: Buffer;
  readonly signatureHeader: string | undefined;
  readonly timestampHeader: string | undefined;
}

export interface TeamsDelivery {
  readonly rawBody: Buffer;
  readonly authorizationHeader: string | undefined;
}

export interface SlackHandlerOptions {
  readonly signingSecret: string;
  readonly api: EvageneApi;
  readonly clock: Clock;
}

export interface TeamsHandlerOptions {
  readonly signingSecret: string;
  readonly api: EvageneApi;
}

export class SlackHandler {
  constructor(private readonly options: SlackHandlerOptions) {}

  async handle(delivery: SlackDelivery): Promise<SlackResponse> {
    if (!verifySlackRequest({
      rawBody: delivery.rawBody,
      signatureHeader: delivery.signatureHeader,
      timestampHeader: delivery.timestampHeader,
      signingSecret: this.options.signingSecret,
      nowSeconds: this.options.clock.nowSeconds(),
    })) {
      return renderSlackError('Signature check failed; request ignored.');
    }
    const pedigreeId = readSlashCommandPedigreeId(delivery.rawBody);
    if (pedigreeId === undefined) {
      return renderSlackError('Usage: /evagene <pedigree-id> (UUID).');
    }
    const report = await tryBuildReport(this.options.api, pedigreeId);
    return report.kind === 'ok' ? renderSlack(report.value) : renderSlackError(report.message);
  }
}

export class TeamsHandler {
  constructor(private readonly options: TeamsHandlerOptions) {}

  async handle(delivery: TeamsDelivery): Promise<TeamsResponse> {
    if (!verifyTeamsRequest({
      rawBody: delivery.rawBody,
      authorizationHeader: delivery.authorizationHeader,
      signingSecret: this.options.signingSecret,
    })) {
      return renderTeamsError('Signature check failed; request ignored.');
    }
    const pedigreeId = readTeamsPedigreeId(delivery.rawBody);
    if (pedigreeId === undefined) {
      return renderTeamsError('Usage: @Evagene <pedigree-id> (UUID).');
    }
    const report = await tryBuildReport(this.options.api, pedigreeId);
    return report.kind === 'ok' ? renderTeams(report.value) : renderTeamsError(report.message);
  }
}

type ReportResult =
  | { readonly kind: 'ok'; readonly value: ChatReport }
  | { readonly kind: 'error'; readonly message: string };

async function tryBuildReport(api: EvageneApi, pedigreeId: string): Promise<ReportResult> {
  try {
    const [summary, nice] = await Promise.all([
      api.getPedigreeSummary(pedigreeId),
      api.calculateNice(pedigreeId),
    ]);
    return {
      kind: 'ok',
      value: {
        summary,
        nice,
        links: {
          webUrl: api.pedigreeWebUrlFor(pedigreeId),
          svgUrl: api.svgUrlFor(pedigreeId),
        },
      },
    };
  } catch (error) {
    if (error instanceof EvageneApiError) {
      return { kind: 'error', message: `Evagene could not complete the request: ${error.message}` };
    }
    throw error;
  }
}

function readSlashCommandPedigreeId(rawBody: Buffer): string | undefined {
  const params = new URLSearchParams(rawBody.toString('utf8'));
  return firstUuid(params.get('text'));
}

function readTeamsPedigreeId(rawBody: Buffer): string | undefined {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawBody.toString('utf8'));
  } catch {
    return undefined;
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return undefined;
  }
  const text = (parsed as Record<string, unknown>).text;
  return typeof text === 'string' ? firstUuid(text) : undefined;
}

function firstUuid(text: string | null): string | undefined {
  if (text === null) {
    return undefined;
  }
  for (const token of text.split(/\s+/)) {
    if (UUID_RE.test(token)) {
      return token;
    }
  }
  return undefined;
}
