/**
 * Express surface: routes `GET /` and `POST /submit`, delegates
 * domain logic to IntakeService.  Kept deliberately thin -- if a
 * framework-level concern creeps in here it probably belongs in
 * IntakeService or IntakeSubmission instead.
 */

import express, { type Express, type Request, type Response } from 'express';

import { EvageneApiError } from './evageneClient.js';
import { IntakeService } from './intakeService.js';
import { IntakeValidationError, parseIntakeSubmission } from './intakeSubmission.js';
import { errorPage, formPage, successPage } from './views.js';

export interface ServerOptions {
  readonly service: IntakeService;
  readonly evageneBaseUrl: string;
}

export function buildServer(options: ServerOptions): Express {
  const app = express();
  app.use(express.urlencoded({ extended: false }));

  app.get('/', (_req: Request, res: Response) => {
    res.type('html').send(formPage());
  });

  app.post('/submit', (req: Request, res: Response) => {
    void handleSubmit(req, res, options);
  });

  return app;
}

async function handleSubmit(
  req: Request,
  res: Response,
  options: ServerOptions,
): Promise<void> {
  let submission;
  try {
    submission = parseIntakeSubmission(req.body as Record<string, unknown>);
  } catch (error) {
    if (error instanceof IntakeValidationError) {
      res.status(400).type('html').send(errorPage({ message: error.message }));
      return;
    }
    throw error;
  }

  try {
    const result = await options.service.create(submission);
    const pedigreeUrl = `${options.evageneBaseUrl.replace(/\/$/, '')}/pedigrees/${result.pedigreeId}`;
    res.type('html').send(
      successPage({
        pedigreeId: result.pedigreeId,
        pedigreeUrl,
        relativesAdded: result.relativesAdded,
      }),
    );
  } catch (error) {
    if (error instanceof EvageneApiError) {
      res.status(502).type('html').send(errorPage({ message: error.message }));
      return;
    }
    throw error;
  }
}
