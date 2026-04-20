import { strictEqual } from 'node:assert/strict';
import { createHmac, randomBytes } from 'node:crypto';
import { test } from 'node:test';

import type { EvageneApi, NiceResult, PedigreeSummary } from '../src/evageneClient.js';
import { SlackHandler, TeamsHandler } from '../src/handlers.js';
import { buildServer } from '../src/server.js';

const PEDIGREE_ID = 'a1cfe665-0000-4000-8000-000000000001';
const SLACK_SECRET = 'slack-signing-secret';
const TEAMS_SECRET = randomBytes(32).toString('base64');

class FixedApi implements EvageneApi {
  lastPedigreeId = '';

  constructor(
    readonly summary: PedigreeSummary,
    readonly nice: NiceResult,
  ) {}
  getPedigreeSummary(pedigreeId: string): Promise<PedigreeSummary> {
    this.lastPedigreeId = pedigreeId;
    return Promise.resolve({ ...this.summary, pedigreeId });
  }
  calculateNice(pedigreeId: string): Promise<NiceResult> {
    this.lastPedigreeId = pedigreeId;
    return Promise.resolve(this.nice);
  }
  svgUrlFor(pedigreeId: string): string {
    return `https://evagene.example/api/pedigrees/${pedigreeId}/export.svg`;
  }
  pedigreeWebUrlFor(pedigreeId: string): string {
    return `https://evagene.example/pedigrees/${pedigreeId}`;
  }
}

function signSlack(body: string, timestamp: number): string {
  const base = `v0:${timestamp.toString()}:${body}`;
  return `v0=${createHmac('sha256', SLACK_SECRET).update(base).digest('hex')}`;
}

function signTeams(body: string): string {
  const key = Buffer.from(TEAMS_SECRET, 'base64');
  return `HMAC ${createHmac('sha256', key).update(body).digest('base64')}`;
}

async function withRunningServer(
  api: EvageneApi,
  body: (port: number) => Promise<void>,
): Promise<void> {
  const nowSeconds = 1_713_614_400;
  const slackHandler = new SlackHandler({
    signingSecret: SLACK_SECRET,
    api,
    clock: { nowSeconds: () => nowSeconds },
  });
  const teamsHandler = new TeamsHandler({ signingSecret: TEAMS_SECRET, api });
  const app = buildServer({ slackHandler, teamsHandler });

  await new Promise<void>((resolve, reject) => {
    const server = app.listen(0, () => {
      const address = server.address();
      if (typeof address !== 'object' || address === null) {
        reject(new Error('Server did not bind to a port.'));
        return;
      }
      body(address.port)
        .then(() => { server.close(() => { resolve(); }); })
        .catch((error: unknown) => {
          server.close(() => {
            reject(error instanceof Error ? error : new Error(String(error)));
          });
        });
    });
  });
}

test('GET /healthz returns 200 ok', async () => {
  const api = new FixedApi(
    { pedigreeId: PEDIGREE_ID, displayName: 'n', probandName: undefined },
    { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] },
  );
  await withRunningServer(api, async port => {
    const response = await fetch(`http://127.0.0.1:${port.toString()}/healthz`);
    strictEqual(response.status, 200);
    strictEqual((await response.text()).trim(), 'ok');
  });
});

test('POST /slack/commands/evagene: correctly signed request is processed end-to-end', async () => {
  const api = new FixedApi(
    { pedigreeId: PEDIGREE_ID, displayName: 'Windsor BRCA branch', probandName: 'Elizabeth' },
    { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] },
  );

  await withRunningServer(api, async port => {
    const body = `token=t&team_id=T&channel_id=C&user_id=U&command=%2Fevagene&text=${PEDIGREE_ID}`;
    const timestamp = 1_713_614_400;
    const response = await fetch(`http://127.0.0.1:${port.toString()}/slack/commands/evagene`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Slack-Request-Timestamp': timestamp.toString(),
        'X-Slack-Signature': signSlack(body, timestamp),
      },
      body,
    });

    strictEqual(response.status, 200);
    const payload = (await response.json()) as { readonly text: string };
    strictEqual(payload.text.includes('Windsor BRCA branch'), true);
    strictEqual(payload.text.includes('GREEN'), true);
  });
});

test('POST /slack/commands/evagene: bad signature yields 200 with a friendly error', async () => {
  const api = new FixedApi(
    { pedigreeId: PEDIGREE_ID, displayName: 'n', probandName: undefined },
    { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] },
  );

  await withRunningServer(api, async port => {
    const body = `text=${PEDIGREE_ID}`;
    const response = await fetch(`http://127.0.0.1:${port.toString()}/slack/commands/evagene`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Slack-Request-Timestamp': '1713614400',
        'X-Slack-Signature': 'v0=' + 'a'.repeat(64),
      },
      body,
    });

    strictEqual(response.status, 200);
    const payload = (await response.json()) as { readonly text: string };
    strictEqual(payload.text.toLowerCase().includes('signature'), true);
  });
});

test('POST /teams/evagene: correctly signed request is processed end-to-end', async () => {
  const api = new FixedApi(
    { pedigreeId: PEDIGREE_ID, displayName: 'Windsor BRCA branch', probandName: 'Elizabeth' },
    { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] },
  );

  await withRunningServer(api, async port => {
    const body = JSON.stringify({ text: `<at>Evagene</at> ${PEDIGREE_ID}` });
    const response = await fetch(`http://127.0.0.1:${port.toString()}/teams/evagene`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: signTeams(body),
      },
      body,
    });

    strictEqual(response.status, 200);
    const payload = (await response.json()) as { readonly title: string; readonly text: string };
    strictEqual(payload.title, 'Windsor BRCA branch');
    strictEqual(payload.text.includes('GREEN'), true);
  });
});

test('POST /teams/evagene: bad signature yields 200 with a friendly error', async () => {
  const api = new FixedApi(
    { pedigreeId: PEDIGREE_ID, displayName: 'n', probandName: undefined },
    { category: 'GREEN', referForGeneticsAssessment: false, triggers: [] },
  );

  await withRunningServer(api, async port => {
    const body = JSON.stringify({ text: PEDIGREE_ID });
    const response = await fetch(`http://127.0.0.1:${port.toString()}/teams/evagene`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `HMAC ${Buffer.alloc(32).toString('base64')}`,
      },
      body,
    });

    strictEqual(response.status, 200);
    const payload = (await response.json()) as { readonly text: string };
    strictEqual(payload.text.toLowerCase().includes('signature'), true);
  });
});
