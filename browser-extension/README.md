# Evagene Pedigree Lookup — browser extension

See a patient ID on any web page — inside your EHR, a pathology report, a spreadsheet, or an email — and get the Evagene pedigree summary in a side panel with one click. No EHR integration project, no data round-trip: the extension reads identifiers off the page you already have open.

> First-time setup (Evagene account, API key, base URL): see [`../getting-started.md`](../getting-started.md). This README assumes you have completed that once.

## Who this is for

- **Clinicians and genetic counsellors** whose workflow touches an EHR that already shows patient identifiers but cannot be modified to embed Evagene directly.
- **Small-clinic IT** who want a zero-integration bridge between an existing system and an Evagene account.
- **Integrators** starting a richer, EHR-specific extension and looking for a correct Manifest V3 skeleton to fork.

## Evagene surface

REST API — specifically `GET /api/pedigrees/{id}/summary`. Full reference at [evagene.net/docs](https://evagene.net/docs).

## Prerequisites

- Evagene account with an API key. A `read`-scope key is sufficient.
- Node.js 20.10 or later (build only — the extension itself runs in the browser).
- Chrome 114+, Edge 114+, or Firefox 128+.

## Run it

This is a Manifest V3 WebExtension, so "running it" means building the bundle and then loading the `dist/` folder into Chrome, Edge, or Firefox as an unpacked extension. The extension itself runs entirely in the browser; there is no server process.

### Build it in Node 20+

```bash
# From the demo root (this folder is the Node project root; there is no node/ subfolder)

# Install dependencies
npm install

# The API key lives in chrome.storage.local — you paste it into the options
# page after loading the extension, so no EVAGENE_API_KEY env var is needed
# at build time.
# Optional: override the base URL at build time if you self-host Evagene.
# Windows PowerShell:
$env:EVAGENE_BASE_URL = "https://evagene.net"
# macOS / Linux (bash / zsh):
export EVAGENE_BASE_URL=https://evagene.net

# Build the bundle into dist/
npm run build

# Rebuild on change (optional)
npm run watch
```

Run the tests and linters (optional):

```bash
npm test
npm run lint
npm run typecheck
npm run manifest-lint
```

## Install the unpacked extension

### Chrome and Edge

1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `dist/` folder.
4. Click the extension icon, then **Options** — paste your `evg_...` API key and save.

### Firefox

1. Open `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on** and select `dist/manifest.json`.
3. Open the extension's options page from `about:addons` and paste your API key.

Temporary add-ons in Firefox are unloaded when the browser closes. For long-running installs, sign the extension with [AMO](https://addons.mozilla.org/).

## Smoke test

1. Build and load the extension per the instructions above.
2. Open the bundled fixture directly: `fixtures/sample-ehr-page.html`. Three UUID-shaped strings appear; each should now have a "View on Evagene" button next to it.
3. Paste a real pedigree UUID from your own Evagene account into any page, or substitute it into the fixture. Click the button. The side panel opens with the pedigree name, proband, and disease list, plus a link to open the pedigree on evagene.net.

If you have not configured an API key yet, the side panel reports "No API key configured" — this is the expected failure mode.

## Configuring the patient-ID regex

The default pattern matches canonical UUIDs. EHRs that use a different identifier format (e.g. `MRN-12345678`) can configure a custom regex on the options page. The options page rejects patterns that would match short, common tokens (for example `\d+`, which would mark every number on the page). Anchor patterns with `\b` and require enough characters to be unambiguous.

## Architecture

```
+---------------------+        runtime.sendMessage        +------------------------+
| content.ts          | --------------------------------> | background.ts          |
| scans DOM,          |                                   | owns API key,          |
| injects buttons     | <-------------------------------- | calls evagene.net,     |
+---------------------+        LookupResponse            | opens side panel       |
                                                         +-----------+------------+
                                                                     |
                                                                     | storage.local (lastSummary)
                                                                     v
                                                         +------------------------+
                                                         | sidePanel.ts           |
                                                         | renders summary        |
                                                         +------------------------+
```

The content script never calls `evagene.net` directly. Manifest V3 explicitly discourages cross-origin fetches from content scripts, and routing every network call through the service worker is the canonical way to keep the API key out of page context — a hostile page cannot read it, and the `host_permissions` declaration is narrow (`https://evagene.net/*`).

## Security

- The API key lives in `chrome.storage.local`, which is not synced across devices.
- Recommended key scope is `read`. The extension only calls `GET /api/pedigrees/{id}/summary`. A read-only key cannot mutate pedigree data.
- The extension emits no telemetry and makes no other network calls.
- The content script runs on `<all_urls>` so it can annotate identifiers in any EHR. Narrow this in `manifest.json`'s `content_scripts.matches` array if you know the exact URLs you care about — the smaller the scope, the smaller the blast radius.

## Browser limits we know about

- **Firefox MV3** implements `sidePanel` via the standardised `sidebar_action` surface in some versions; the `sidePanel.open({tabId})` call is non-standard and may be a no-op on Firefox. The side panel HTML still loads when the user toggles the sidebar manually, so the summary renders correctly once opened. Chrome and Edge (Chromium) support programmatic opening.
- **Firefox** requires `browser_specific_settings.gecko.id` in the manifest — included.
- **Chrome MV3 service workers** are terminated aggressively. The extension keeps no in-memory state across a lookup, so this is harmless.

## Caveats

This is an example integration, not a clinical decision tool. It displays information returned by the Evagene API; all interpretation and any action taken belongs to the clinician.
