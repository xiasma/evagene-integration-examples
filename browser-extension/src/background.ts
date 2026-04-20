/**
 * Background service worker — the only place the API key is ever held
 * in memory. Content scripts and the side panel exchange typed messages
 * with this worker; the worker calls evagene.net on their behalf.
 */

import { EvageneClient, EvageneError } from './evageneClient.js';
import type { LookupRequest, LookupResponse, PedigreeSummary } from './messaging.js';
import { failure, route } from './messaging.js';
import { readSettings } from './storage.js';

const handlers = {
  'lookup-pedigree': handleLookup,
};

chrome.runtime.onMessage.addListener(
  (message: unknown, sender, sendResponse: (response: LookupResponse) => void) => {
    respond(message, sender, sendResponse);
    return true;
  },
);

function respond(
  message: unknown,
  sender: chrome.runtime.MessageSender,
  sendResponse: (response: LookupResponse) => void,
): void {
  route(message, handlers)
    .then(async response => {
      sendResponse(response);
      if (response.ok) await openSidePanelFor(sender);
    })
    .catch((error: unknown) => {
      const reason = error instanceof Error ? error.message : String(error);
      sendResponse(failure(reason));
    });
}

async function handleLookup(message: LookupRequest): Promise<LookupResponse> {
  const { apiKey, baseUrl } = await readSettings();
  if (apiKey === '') {
    return failure('No API key configured. Open the extension options and paste your evg_... key.');
  }
  const client = new EvageneClient({ apiKey, baseUrl, fetch: fetch.bind(globalThis) });
  try {
    const summary = await client.getPedigreeSummary(message.pedigreeId);
    await cacheLastSummary(summary);
    return { kind: 'lookup-result', ok: true, summary };
  } catch (error) {
    const reason = error instanceof EvageneError ? error.message : String(error);
    return failure(reason);
  }
}

async function cacheLastSummary(summary: PedigreeSummary): Promise<void> {
  await chrome.storage.local.set({ lastSummary: summary });
}

async function openSidePanelFor(sender: chrome.runtime.MessageSender): Promise<void> {
  const tabId = sender.tab?.id;
  if (tabId === undefined) return;
  await chrome.sidePanel.open({ tabId });
}
