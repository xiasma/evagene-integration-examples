/**
 * Side-panel UI. Listens for the most recently cached summary the
 * background worker stored after a successful lookup, and re-renders
 * when a new lookup completes.
 */

import type { PedigreeSummary } from './messaging.js';

interface Dom {
  readonly empty: HTMLElement;
  readonly summary: HTMLElement;
  readonly name: HTMLElement;
  readonly proband: HTMLElement;
  readonly diseases: HTMLElement;
  readonly viewLink: HTMLAnchorElement;
  readonly error: HTMLElement;
}

function bind(): Dom {
  return {
    empty: requireElement('empty'),
    summary: requireElement('summary'),
    name: requireElement('name'),
    proband: requireElement('proband'),
    diseases: requireElement('diseases'),
    viewLink: requireElement('viewLink') as HTMLAnchorElement,
    error: requireElement('error'),
  };
}

function requireElement(id: string): HTMLElement {
  const element = document.getElementById(id);
  if (element === null) throw new Error(`Missing #${id}`);
  return element;
}

function render(dom: Dom, summary: PedigreeSummary): void {
  dom.empty.hidden = true;
  dom.error.hidden = true;
  dom.summary.hidden = false;
  dom.name.textContent = summary.name;
  dom.proband.textContent =
    summary.probandName !== null ? `Proband: ${summary.probandName}` : 'No proband recorded.';
  dom.diseases.replaceChildren(...summary.diseases.map(toListItem));
  dom.viewLink.href = summary.viewUrl;
}

function renderError(dom: Dom, message: string): void {
  dom.empty.hidden = true;
  dom.summary.hidden = true;
  dom.error.hidden = false;
  dom.error.textContent = message;
}

function toListItem(disease: string): HTMLLIElement {
  const item = document.createElement('li');
  item.textContent = disease;
  return item;
}

async function init(): Promise<void> {
  const dom = bind();
  const stored = await chrome.storage.local.get('lastSummary');
  const cached = stored.lastSummary as PedigreeSummary | undefined;
  if (cached !== undefined) render(dom, cached);

  chrome.storage.onChanged.addListener(changes => {
    const change = changes.lastSummary;
    if (change?.newValue !== undefined) {
      render(dom, change.newValue as PedigreeSummary);
    }
  });

  chrome.runtime.onMessage.addListener(message => {
    if (isLookupFailure(message)) renderError(dom, message.error);
  });
}

function isLookupFailure(
  value: unknown,
): value is { kind: 'lookup-result'; ok: false; error: string } {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as { kind?: unknown; ok?: unknown; error?: unknown };
  return (
    candidate.kind === 'lookup-result' &&
    candidate.ok === false &&
    typeof candidate.error === 'string'
  );
}

void init();
