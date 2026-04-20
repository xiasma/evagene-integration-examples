/**
 * Express surface: three routes, no business logic.  Everything
 * non-HTTP lives in WebhookHandler and EventStore.
 */

import express, { type Express, type Request, type Response } from 'express';

import type { EventStore } from './eventStore.js';
import type { WebhookHandler, WebhookOutcome } from './webhookHandler.js';

const DEFAULT_PAGE_SIZE = 100;
const MAX_PAGE_SIZE = 1000;

export interface ServerOptions {
  readonly handler: WebhookHandler;
  readonly store: EventStore;
}

export function buildServer(options: ServerOptions): Express {
  const app = express();

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

  return app;
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
