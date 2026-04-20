/**
 * Express surface: routes only, no business logic.
 *
 *  GET  /                      dashboard HTML
 *  GET  /events-stream         Server-Sent Events fan-out of new webhook events
 *  POST /webhook               HMAC-verified delivery endpoint (204 on success)
 *  GET  /events                Audit log as JSON Lines
 *  GET  /events/verify         Hash-chain verdict
 *  GET  /pedigree-card/:id     HTML fragment (server-rendered)
 *  GET  /healthz               Liveness probe
 */

import express, { type Express, type Request, type Response } from 'express';

import type { EvageneApi } from './evageneClient.js';
import { EvageneApiError } from './evageneClient.js';
import type { EventStore } from './eventStore.js';
import { ResponseSchemaError, classifyNiceResponse } from './niceClassifier.js';
import type { DashboardEvent, EventSubscriptionHub } from './sseBroker.js';
import { dashboardPage, pedigreeCardError, pedigreeCardFragment } from './views.js';
import type { WebhookHandler, WebhookOutcome } from './webhookHandler.js';

const DEFAULT_PAGE_SIZE = 100;
const MAX_PAGE_SIZE = 1000;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface ServerOptions {
  readonly handler: WebhookHandler;
  readonly store: EventStore;
  readonly broker: EventSubscriptionHub;
  readonly evagene: EvageneApi;
}

export function buildServer(options: ServerOptions): Express {
  const app = express();

  app.get('/healthz', (_req: Request, res: Response) => {
    res.type('text/plain').send('ok');
  });

  app.get('/', (_req: Request, res: Response) => {
    res.type('html').send(dashboardPage());
  });

  app.get('/events-stream', (req: Request, res: Response) => {
    openEventStream(req, res, options.broker);
  });

  app.post(
    '/webhook',
    express.raw({ type: '*/*', limit: '1mb' }),
    (req: Request, res: Response) => {
      respondToOutcome(
        res,
        options.handler.handle({
          rawBody: rawBodyOf(req),
          signatureHeader: headerOf(req, 'x-evagene-signature-256'),
          eventTypeHeader: headerOf(req, 'x-evagene-event'),
        }),
      );
    },
  );

  app.get('/events', (req: Request, res: Response) => {
    const { limit, offset } = parsePagination(req);
    const rows = options.store.list(limit, offset);
    res.type('application/x-ndjson');
    for (const row of rows) {
      res.write(`${JSON.stringify(row)}\n`);
    }
    res.end();
  });

  app.get('/events/verify', (_req: Request, res: Response) => {
    const result = options.store.verifyChain();
    res.json({ ok: result.ok, break_at: result.breakAt });
  });

  app.get('/pedigree-card/:id', (req: Request, res: Response) => {
    void renderPedigreeCard(req, res, options.evagene);
  });

  return app;
}

function openEventStream(req: Request, res: Response, broker: EventSubscriptionHub): void {
  res.status(200);
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();
  res.write('retry: 2000\n\n');

  const unsubscribe = broker.subscribe(event => {
    res.write(`event: webhook\n`);
    res.write(`id: ${event.id.toString()}\n`);
    res.write(`data: ${JSON.stringify(toDashboardPayload(event))}\n\n`);
  });

  req.on('close', () => {
    unsubscribe();
    res.end();
  });
}

async function renderPedigreeCard(
  req: Request,
  res: Response,
  evagene: EvageneApi,
): Promise<void> {
  const raw = req.params.id;
  const pedigreeId = typeof raw === 'string' ? raw.trim() : '';
  if (!UUID_RE.test(pedigreeId)) {
    res.status(400).type('html').send(pedigreeCardError('Invalid pedigree id.'));
    return;
  }

  try {
    const [summary, svg, niceRaw] = await Promise.all([
      evagene.getPedigreeSummary(pedigreeId),
      evagene.fetchEmbedSvg(pedigreeId),
      evagene.calculateNice(pedigreeId),
    ]);
    const nice = classifyNiceResponse(niceRaw);
    res.type('html').send(
      pedigreeCardFragment({
        pedigreeId,
        displayName: summary.displayName,
        svg,
        nice,
      }),
    );
  } catch (error) {
    if (error instanceof EvageneApiError || error instanceof ResponseSchemaError) {
      res.status(502).type('html').send(pedigreeCardError(error.message));
      return;
    }
    throw error;
  }
}

function toDashboardPayload(event: DashboardEvent): Record<string, unknown> {
  return {
    id: event.id,
    eventType: event.eventType,
    receivedAt: event.receivedAt,
    body: event.body,
  };
}

function rawBodyOf(req: Request): Buffer {
  return Buffer.isBuffer(req.body) ? req.body : Buffer.alloc(0);
}

function headerOf(req: Request, name: string): string | undefined {
  const value = req.headers[name];
  if (typeof value === 'string') {
    return value;
  }
  return Array.isArray(value) ? value[0] : undefined;
}

function respondToOutcome(res: Response, outcome: WebhookOutcome): void {
  switch (outcome.status) {
    case 'accepted':
      res.status(204).end();
      return;
    case 'bad_signature':
      res.status(401).type('text/plain').send('Invalid signature.');
      return;
    case 'bad_request':
      res.status(400).type('text/plain').send(outcome.reason);
      return;
  }
}

function parsePagination(req: Request): { readonly limit: number; readonly offset: number } {
  return {
    limit: clamp(readInt(req.query.limit, DEFAULT_PAGE_SIZE), 1, MAX_PAGE_SIZE),
    offset: Math.max(0, readInt(req.query.offset, 0)),
  };
}

function readInt(raw: unknown, fallback: number): number {
  if (typeof raw !== 'string') {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value: number, lower: number, upper: number): number {
  return Math.min(Math.max(value, lower), upper);
}
