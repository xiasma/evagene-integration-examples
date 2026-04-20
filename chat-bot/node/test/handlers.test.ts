import { deepStrictEqual, strictEqual } from 'node:assert/strict';
import { createHmac, randomBytes } from 'node:crypto';
import { test } from 'node:test';

import type { EvageneApi, NiceResult, PedigreeSummary } from '../src/evageneClient.js';
import { EvageneApiError } from '../src/evageneClient.js';
import { SlackHandler, TeamsHandler } from '../src/handlers.js';

const PEDIGREE_ID = 'a1cfe665-0000-4000-8000-000000000001';
const SLACK_SECRET = 'slack-signing-secret';
const TEAMS_SECRET = randomBytes(32).toString('base64');
const NOW = 1_713_614_400;

class FakeApi implements EvageneApi {
  summary: PedigreeSummary = {
    pedigreeId: PEDIGREE_ID,
    displayName: 'Windsor BRCA branch',
    probandName: 'Elizabeth',
  };
  nice: NiceResult = {
    category: 'GREEN',
    triggers: [],
    referForGeneticsAssessment: false,
  };
  failWith: Error | undefined = undefined;

  getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary> {
    if (this.failWith !== undefined) {
      return Promise.reject(this.failWith);
    }
    return Promise.resolve({ ...this.summary, pedigreeId });
  }
  calculateNice(pedigreeId: string): Promise<NiceResult> {
    this.lastNicePedigreeId = pedigreeId;
    if (this.failWith !== undefined) {
      return Promise.reject(this.failWith);
    }
    return Promise.resolve(this.nice);
  }
  lastNicePedigreeId: string | undefined = undefined;
  svgUrlFor(pedigreeId: string): string {
    return `https://evagene.example/api/pedigrees/${pedigreeId}/export.svg`;
  }
  pedigreeWebUrlFor(pedigreeId: string): string {
    return `https://evagene.example/pedigrees/${pedigreeId}`;
  }
}

function signSlack(body: Buffer, timestamp: number, secret: string): string {
  const base = Buffer.concat([Buffer.from(`v0:${timestamp.toString()}:`, 'utf8'), body]);
  return `v0=${createHmac('sha256', secret).update(base).digest('hex')}`;
}

function signTeams(body: Buffer, secret: string): string {
  const key = Buffer.from(secret, 'base64');
  return `HMAC ${createHmac('sha256', key).update(body).digest('base64')}`;
}

function slackHandler(api: EvageneApi): SlackHandler {
  return new SlackHandler({
    signingSecret: SLACK_SECRET,
    api,
    clock: { nowSeconds: () => NOW },
  });
}

function teamsHandler(api: EvageneApi): TeamsHandler {
  return new TeamsHandler({ signingSecret: TEAMS_SECRET, api });
}

test('Slack: valid signed request with UUID produces an in_channel response', async () => {
  const api = new FakeApi();
  api.nice = { category: 'RED', referForGeneticsAssessment: true, triggers: ['Mother affected <40'] };
  const body = Buffer.from(`token=t&text=${PEDIGREE_ID}&command=%2Fevagene`, 'utf8');

  const response = await slackHandler(api).handle({
    rawBody: body,
    signatureHeader: signSlack(body, NOW, SLACK_SECRET),
    timestampHeader: NOW.toString(),
  });

  strictEqual(response.response_type, 'in_channel');
  strictEqual(response.text.includes('Windsor BRCA branch'), true);
  strictEqual(response.text.includes('RED'), true);
});

test('Slack: bad signature returns a rendered error (never throws)', async () => {
  const api = new FakeApi();
  const body = Buffer.from(`text=${PEDIGREE_ID}`, 'utf8');

  const response = await slackHandler(api).handle({
    rawBody: body,
    signatureHeader: 'v0=' + 'a'.repeat(64),
    timestampHeader: NOW.toString(),
  });

  strictEqual(response.text.toLowerCase().includes('signature'), true);
});

test('Slack: non-UUID text returns a usage message', async () => {
  const api = new FakeApi();
  const body = Buffer.from('text=hello', 'utf8');

  const response = await slackHandler(api).handle({
    rawBody: body,
    signatureHeader: signSlack(body, NOW, SLACK_SECRET),
    timestampHeader: NOW.toString(),
  });

  strictEqual(response.text.toLowerCase().includes('usage'), true);
});

test('Slack: Evagene API error becomes an in-channel error message', async () => {
  const api = new FakeApi();
  api.failWith = new EvageneApiError('HTTP 503');
  const body = Buffer.from(`text=${PEDIGREE_ID}`, 'utf8');

  const response = await slackHandler(api).handle({
    rawBody: body,
    signatureHeader: signSlack(body, NOW, SLACK_SECRET),
    timestampHeader: NOW.toString(),
  });

  strictEqual(response.text.includes('HTTP 503'), true);
});

test('Teams: valid signed request with UUID produces a MessageCard', async () => {
  const api = new FakeApi();
  api.nice = { category: 'AMBER', referForGeneticsAssessment: true, triggers: ['Cousin affected'] };
  const body = Buffer.from(JSON.stringify({ text: `<at>Evagene</at> ${PEDIGREE_ID}` }), 'utf8');

  const response = await teamsHandler(api).handle({
    rawBody: body,
    authorizationHeader: signTeams(body, TEAMS_SECRET),
  });

  strictEqual(response['@type'], 'MessageCard');
  strictEqual(response.title, 'Windsor BRCA branch');
  strictEqual(response.text.includes('AMBER'), true);
  deepStrictEqual(
    response.potentialAction.map(action => action.name),
    ['View pedigree', 'Download SVG'],
  );
});

test('Teams: bad signature returns a rendered error card', async () => {
  const api = new FakeApi();
  const body = Buffer.from(JSON.stringify({ text: PEDIGREE_ID }), 'utf8');

  const response = await teamsHandler(api).handle({
    rawBody: body,
    authorizationHeader: `HMAC ${Buffer.alloc(32).toString('base64')}`,
  });

  strictEqual(response.text.toLowerCase().includes('signature'), true);
});

test('Teams: non-JSON body returns a usage message', async () => {
  const api = new FakeApi();
  const body = Buffer.from('not-json', 'utf8');

  const response = await teamsHandler(api).handle({
    rawBody: body,
    authorizationHeader: signTeams(body, TEAMS_SECRET),
  });

  strictEqual(response.text.toLowerCase().includes('usage'), true);
});
