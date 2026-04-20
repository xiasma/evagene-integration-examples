/**
 * Server-side views: the full dashboard page and a pedigree-card
 * fragment.  Kept in a typed module rather than a template engine so
 * the demo ships with zero extra runtime deps and is still readable.
 */

import type { NiceCategory, NiceOutcome } from './niceClassifier.js';

const DASHBOARD_STYLE = `
  :root { --fg: #1f2937; --muted: #6b7280; --border: #e5e7eb; --bg: #faf8f5;
          --green: #16a34a; --amber: #d97706; --red: #dc2626; --accent: #4f46b8; }
  * { box-sizing: border-box; }
  body { font: 1rem/1.5 system-ui, sans-serif; color: var(--fg); background: var(--bg);
         margin: 0; padding: 1.5rem; }
  header { display: flex; justify-content: space-between; align-items: baseline;
           margin: 0 auto 1.5rem; max-width: 72rem; }
  header h1 { margin: 0; font-size: 1.375rem; }
  header .status { font-size: 0.875rem; color: var(--muted); }
  header .status[data-live="yes"]::before { content: "\u25CF "; color: var(--green); }
  header .status[data-live="no"]::before  { content: "\u25CF "; color: var(--red); }
  main { max-width: 72rem; margin: 0 auto; }
  .empty { color: var(--muted); padding: 2rem 0; text-align: center; }
  .cards { display: grid; gap: 0.75rem; }
  .card { background: white; border: 1px solid var(--border); border-radius: 8px;
          padding: 0.875rem 1rem; cursor: pointer; transition: border-color 120ms; }
  .card:hover { border-color: var(--accent); }
  .card .event { font-size: 0.75rem; color: var(--muted); text-transform: uppercase;
                 letter-spacing: 0.05em; }
  .card .id { font-family: ui-monospace, monospace; font-size: 0.875rem; margin-top: 0.25rem; }
  .card .body { margin-top: 0.5rem; display: none; }
  .card[aria-expanded="true"] .body { display: block; }
  .card .svg-wrap { overflow: auto; background: white; border: 1px solid var(--border);
                    border-radius: 6px; padding: 0.5rem; margin-top: 0.5rem; }
  .card .svg-wrap svg { max-width: 100%; height: auto; }
  .nice { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 999px;
          font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
  .nice.near_population { background: #dcfce7; color: var(--green); }
  .nice.moderate        { background: #fef3c7; color: var(--amber); }
  .nice.high            { background: #fee2e2; color: var(--red); }
  .error { color: var(--red); font-size: 0.875rem; margin-top: 0.5rem; }
`.trim();

const DASHBOARD_SCRIPT = `
  const cards = document.getElementById('cards');
  const empty = document.getElementById('empty');
  const status = document.getElementById('status');
  const RELEVANT = new Set(['pedigree.created','pedigree.updated','import.completed']);

  function setLive(isLive) {
    status.dataset.live = isLive ? 'yes' : 'no';
    status.textContent = isLive ? 'Live' : 'Disconnected';
  }

  function extractPedigreeId(bodyJson) {
    try {
      const payload = JSON.parse(bodyJson);
      return payload.pedigree_id || payload.id || null;
    } catch { return null; }
  }

  function addCard(event) {
    const pedigreeId = extractPedigreeId(event.body);
    if (!pedigreeId) return;
    if (empty) empty.remove();
    const card = document.createElement('article');
    card.className = 'card';
    card.setAttribute('aria-expanded', 'false');
    card.innerHTML =
      '<div class="event"></div>' +
      '<div class="id"></div>' +
      '<div class="body"></div>';
    card.querySelector('.event').textContent = event.eventType + ' \u00B7 ' + event.receivedAt;
    card.querySelector('.id').textContent = pedigreeId;
    card.addEventListener('click', () => { toggleCard(card, pedigreeId); });
    cards.insertBefore(card, cards.firstChild);
  }

  async function toggleCard(card, pedigreeId) {
    const expanded = card.getAttribute('aria-expanded') === 'true';
    if (expanded) { card.setAttribute('aria-expanded', 'false'); return; }
    const body = card.querySelector('.body');
    if (!body.dataset.loaded) {
      body.textContent = 'Loading...';
      try {
        const resp = await fetch('/pedigree-card/' + encodeURIComponent(pedigreeId));
        body.innerHTML = await resp.text();
      } catch (err) {
        body.innerHTML = '<p class="error">Failed to load pedigree card.</p>';
      }
      body.dataset.loaded = '1';
    }
    card.setAttribute('aria-expanded', 'true');
  }

  const stream = new EventSource('/events-stream');
  stream.onopen = () => { setLive(true); };
  stream.onerror = () => { setLive(false); };
  stream.addEventListener('webhook', (ev) => {
    const event = JSON.parse(ev.data);
    if (RELEVANT.has(event.eventType)) addCard(event);
  });
`.trim();

export function dashboardPage(): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Clinic triage dashboard</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>${DASHBOARD_STYLE}</style>
</head>
<body>
  <header>
    <h1>Clinic triage dashboard</h1>
    <span id="status" class="status" data-live="no">Connecting...</span>
  </header>
  <main>
    <section id="cards" class="cards">
      <p id="empty" class="empty">Waiting for the next pedigree webhook delivery...</p>
    </section>
  </main>
  <script>${DASHBOARD_SCRIPT}</script>
</body>
</html>`;
}

export interface PedigreeCardModel {
  readonly pedigreeId: string;
  readonly displayName: string;
  readonly svg: string;
  readonly nice: NiceOutcome;
}

export function pedigreeCardFragment(model: PedigreeCardModel): string {
  const label = niceLabel(model.nice.category);
  const referral = model.nice.referForGeneticsAssessment
    ? 'Refer for genetics assessment.'
    : 'No genetics referral indicated by NICE.';
  return `
    <p><strong>${escapeHtml(model.displayName)}</strong> <span class="nice ${model.nice.category}">${label}</span></p>
    <p class="muted">${escapeHtml(referral)}</p>
    <div class="svg-wrap">${model.svg}</div>
  `.trim();
}

export function pedigreeCardError(message: string): string {
  return `<p class="error">${escapeHtml(message)}</p>`;
}

const NICE_LABELS: Readonly<Record<NiceCategory, string>> = {
  near_population: 'Near-population risk',
  moderate: 'Moderate risk',
  high: 'High risk',
};

function niceLabel(category: NiceCategory): string {
  return NICE_LABELS[category];
}

export function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
