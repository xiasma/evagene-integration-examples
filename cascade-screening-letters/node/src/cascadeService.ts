/**
 * Orchestrator: selector + resolver + one template run + writer per relative.
 *
 * Knows the sequence of calls but no HTTP and no filesystem. The template
 * is executed once per pedigree: the server endpoint doesn't accept a
 * per-individual target, so running it N times would burn quota for nothing.
 */

import type { EvageneApi } from './evageneClient.js';
import { composeLetter, type LetterSink } from './letterWriter.js';
import { type LetterTarget, selectAtRiskRelatives } from './relativeSelector.js';
import { resolveTemplateId } from './templateResolver.js';

export class NoAtRiskRelativesError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NoAtRiskRelativesError';
  }
}

export interface CascadeRequest {
  readonly pedigreeId: string;
  readonly templateOverride?: string;
  readonly dryRun: boolean;
}

export interface CascadeResult {
  readonly targets: readonly LetterTarget[];
  readonly writtenPaths: readonly string[];
}

export interface CascadeServiceOptions {
  readonly client: EvageneApi;
  readonly sink: LetterSink;
}

export class CascadeService {
  private readonly client: EvageneApi;
  private readonly sink: LetterSink;

  constructor(options: CascadeServiceOptions) {
    this.client = options.client;
    this.sink = options.sink;
  }

  async generateLetters(request: CascadeRequest): Promise<CascadeResult> {
    const targets = await this.selectTargets(request.pedigreeId);
    if (request.dryRun) {
      return { targets, writtenPaths: [] };
    }
    const templateBody = await this.renderTemplate(request);
    const writtenPaths = targets.map((target, index) =>
      this.sink.write(composeLetter(target, templateBody, index + 1)),
    );
    return { targets, writtenPaths };
  }

  private async selectTargets(pedigreeId: string): Promise<readonly LetterTarget[]> {
    const register = await this.client.fetchRegister(pedigreeId);
    if (register.probandId === null) {
      throw new NoAtRiskRelativesError(
        `Pedigree ${pedigreeId} has no designated proband; ` +
          `set one in the Evagene web app before running this tool.`,
      );
    }
    const targets = selectAtRiskRelatives(register);
    if (targets.length === 0) {
      throw new NoAtRiskRelativesError(
        `Pedigree ${pedigreeId} has no first- or second-degree relatives with a display name recorded.`,
      );
    }
    return targets;
  }

  private async renderTemplate(request: CascadeRequest): Promise<string> {
    const templateId = await resolveTemplateId(this.client, request.templateOverride);
    return this.client.runTemplate(templateId, request.pedigreeId);
  }
}
