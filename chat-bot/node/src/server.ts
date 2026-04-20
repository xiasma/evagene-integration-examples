/**
 * Express routes. Keeps framework concerns here; the handlers are
 * framework-free. Each signed route reads the raw body (Slack and Teams
 * both sign the exact bytes they sent, so parsing the body before
 * verifying the signature would break the HMAC).
 */

import express, { type Express, type Request, type Response } from 'express';

import type { SlackHandler, TeamsHandler } from './handlers.js';

const RAW_BODY_LIMIT = '1mb';

export interface ServerOptions {
  readonly slackHandler: SlackHandler | undefined;
  readonly teamsHandler: TeamsHandler | undefined;
}

export function buildServer(options: ServerOptions): Express {
  const app = express();

  app.get('/healthz', (_req: Request, res: Response) => {
    res.type('text/plain').send('ok');
  });

  if (options.slackHandler !== undefined) {
    registerSlackRoute(app, options.slackHandler);
  }
  if (options.teamsHandler !== undefined) {
    registerTeamsRoute(app, options.teamsHandler);
  }
  return app;
}

function registerSlackRoute(app: Express, handler: SlackHandler): void {
  app.post(
    '/slack/commands/evagene',
    express.raw({ type: '*/*', limit: RAW_BODY_LIMIT }),
    (req: Request, res: Response) => {
      handler
        .handle({
          rawBody: rawBodyOf(req),
          signatureHeader: headerOf(req, 'x-slack-signature'),
          timestampHeader: headerOf(req, 'x-slack-request-timestamp'),
        })
        .then(payload => {
          res.status(200).json(payload);
        })
        .catch((error: unknown) => {
          sendUnexpectedError(res, error);
        });
    },
  );
}

function registerTeamsRoute(app: Express, handler: TeamsHandler): void {
  app.post(
    '/teams/evagene',
    express.raw({ type: '*/*', limit: RAW_BODY_LIMIT }),
    (req: Request, res: Response) => {
      handler
        .handle({
          rawBody: rawBodyOf(req),
          authorizationHeader: headerOf(req, 'authorization'),
        })
        .then(payload => {
          res.status(200).json(payload);
        })
        .catch((error: unknown) => {
          sendUnexpectedError(res, error);
        });
    },
  );
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

function sendUnexpectedError(res: Response, error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`unexpected error handling chat request: ${message}\n`);
  res.status(200).json({ text: 'Evagene bot hit an unexpected error; see server logs.' });
}
