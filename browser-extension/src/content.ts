/**
 * Content-script entry point. Reads the configured pattern from storage,
 * annotates the page, and forwards clicks to the background worker which
 * owns the API key. This script never talks to evagene.net directly —
 * that would violate the MV3 content-script security model.
 */

import { annotate } from './contentInjector.js';
import type { LookupRequest } from './messaging.js';
import { validatePattern } from './patternValidator.js';
import { readSettings } from './storage.js';

async function main(): Promise<void> {
  const { patternSource } = await readSettings();
  const validation = validatePattern(patternSource);
  if (!validation.ok) return;

  annotate({
    root: document.body,
    pattern: validation.pattern,
    onClick: sendLookup,
  });
}

function sendLookup(pedigreeId: string): void {
  const message: LookupRequest = { kind: 'lookup-pedigree', pedigreeId };
  void chrome.runtime.sendMessage(message);
}

void main();
