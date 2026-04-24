# Referral dashboard

**A live card view of Evagene webhook events.** Register this server as a webhook endpoint in [Evagene](https://evagene.net) and every new pedigree (and every finished import) appears as a card on a shared web dashboard within milliseconds. Click a card and the pedigree is drawn inline with its NICE category labelled.

This is an academic / research example of a two-layer receiver: a hash-chained audit blotter underneath, and a Server-Sent Events dashboard on top. It is a reference implementation to read and fork — not a clinical intake product.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Integrators and developers** building a bespoke front-end on top of Evagene webhooks — the two-layer split (audit-blotter + dashboard) is a copy-paste starting point.
- **Researchers and educators** wanting a live view of webhook deliveries against a synthetic or de-identified dataset, to observe how pedigree events flow through the system.
- **Students** studying an end-to-end Server-Sent Events pattern (signed receiver → persistence → pub/sub → live DOM updates) in a small codebase.

## What Evagene surface this uses

- **Webhooks** — HMAC-SHA256-signed outbound POSTs from Evagene to this server. The relevant events are `pedigree.created`, `pedigree.updated`, `pedigree.deleted`, `individual.created`, `individual.updated`, `individual.deleted`, `analysis.completed`, `import.completed`.
- **REST API** — `GET /api/embed/{id}/svg` for the inline pedigree drawing, `POST /api/pedigrees/{id}/risk/calculate` for the NICE category, `GET /api/pedigrees/{id}` for the display name.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) or [https://evagene.net/redoc](https://evagene.net/redoc).

Each Evagene delivery arrives with:

- `X-Evagene-Event` — the event name (e.g. `pedigree.created`).
- `X-Evagene-Signature-256` — `sha256=` followed by a hex HMAC-SHA256 of the raw request body, computed with the per-webhook secret.
- `X-Evagene-Delivery` — a per-delivery UUID.

The dashboard filters the real-time card stream to `pedigree.created`, `pedigree.updated`, and `import.completed`, but every event is persisted to the audit log so nothing is dropped.

## Prerequisites

1. An Evagene account and an API key with the `read` and `analyze` scopes — see [getting-started.md](../getting-started.md).
2. A publicly reachable URL (or a tunnel — `ngrok`, `cloudflared`) so Evagene can reach the server.
3. A webhook registered against your URL via `POST /api/webhooks`. The response returns the secret *once* — paste it into `EVAGENE_WEBHOOK_SECRET`.
4. Node.js 20.10 or later.

## Configuration

Copy `node/.env.example` to `node/.env` and fill in the values.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EVAGENE_API_KEY`        | yes | — | Used to fetch the embed SVG and run the NICE calculation for each card. |
| `EVAGENE_WEBHOOK_SECRET` | yes | — | The secret returned when the webhook was created. |
| `EVAGENE_BASE_URL`       | no  | `https://evagene.net` | Override only for a private Evagene deployment. |
| `PORT`                   | no  | `4000` | TCP port the HTTP server binds. |
| `SQLITE_PATH`            | no  | `./dashboard.db` | File path for the audit log. |

## HTTP contract

| Method | Path                   | Behaviour |
|--------|------------------------|-----------|
| `GET`  | `/`                    | Dashboard HTML. The inline script subscribes to `/events-stream`. |
| `GET`  | `/events-stream`       | Server-Sent Events; every persisted webhook is fanned out as an `event: webhook` frame. |
| `POST` | `/webhook`             | Verifies `X-Evagene-Signature-256` against the raw body, persists the event, fans it out, returns `204`. Bad signature `401`, non-JSON body `400`. |
| `GET`  | `/events`              | The audit log as JSON Lines. `?limit=100&offset=0`. |
| `GET`  | `/events/verify`       | Recomputes the hash chain. `{"ok": true, "break_at": null}` on success. |
| `GET`  | `/pedigree-card/:id`   | Server-rendered HTML fragment: the Evagene embed SVG, the NICE category, and the pedigree display name. |
| `GET`  | `/healthz`             | `200 ok` liveness probe. |

## Run it

Only a Node implementation ships. Startup prints:

```
Referral dashboard listening on http://localhost:4000/
```

Open `http://localhost:4000/` in a browser. The header shows "Live" once the SSE connection is up. Trigger a pedigree create in Evagene (or synthesise a signed delivery — see below) and a card appears at the top of the list.

### Run it in Node 20+

```bash
cd node

# Install dependencies
npm install

# Set your API key, webhook secret, and optional overrides (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
$env:EVAGENE_WEBHOOK_SECRET = "replace_with_secret_from_webhook_creation_response"
$env:PORT = "4000"
$env:SQLITE_PATH = "./dashboard.db"
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...
export EVAGENE_WEBHOOK_SECRET=replace_with_secret_from_webhook_creation_response
export PORT=4000
export SQLITE_PATH=./dashboard.db

# Run the server
npm start
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

## Smoke test (no real Evagene delivery needed)

```bash
export EVAGENE_WEBHOOK_SECRET=shhh
BODY="$(cat fixtures/sample-webhook-pedigree-created.json)"
SIG=$(printf %s "$BODY" | openssl dgst -sha256 -hmac "$EVAGENE_WEBHOOK_SECRET" -r | awk '{print $1}')
curl -i -X POST http://localhost:4000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Evagene-Event: pedigree.created" \
  -H "X-Evagene-Signature-256: sha256=$SIG" \
  --data-binary "$BODY"
```

Expected: `204` on `/webhook`, an SSE frame on `/events-stream`, a JSON-lines row from `/events`, and `{"ok":true,"break_at":null}` from `/events/verify`.

## Architecture

```
              (Evagene)
                 │ signed POST
                 ▼
 ┌────────────────────────────────┐
 │  /webhook  (Express + raw body)│
 └───┬────────────────────────────┘
     │
     ▼
 SignatureVerifier (constant-time HMAC)
     │ ok
     ▼
 WebhookHandler ──► EventStore (SQLite, hash-chained rows)
     │
     ▼
 SseBroker ──► /events-stream subscribers  (triage-nurse browsers)
                               │
                   click a card │
                               ▼
                     /pedigree-card/:id
                               │
                               ▼
              EvageneClient: embed SVG + NICE + display name
```

The **blotter layer** (SignatureVerifier, EventStore, WebhookHandler) is the same pattern used in the [webhook-audit-blotter](../webhook-audit-blotter) demo. The **dashboard layer** adds an in-process pub/sub broker (`SseBroker`), the live SSE route, the HTML views, and a thin `EvageneClient` for the on-click card lookup.

## Caveats

- This is an **academic / research example, not a validated clinical tool**, not a medical device, and not fit for patient care. Use synthetic or de-identified pedigrees — never drive referral or care decisions from the dashboard.
- **Single-node demo.** The SSE broker and SQLite audit log are in-process. Anything more ambitious needs an external pub/sub (Redis, NATS) and a durable append-only store.
- **NICE category only.** The dashboard surfaces the NICE label that Evagene returns. For other models (Tyrer-Cuzick, BOADICEA, BRCAPRO), see the [nice-traffic-light](../nice-traffic-light) and [canrisk-bridge](../canrisk-bridge) demos.
- **Audit log trust.** The hash chain detects tampering after the fact — see the [webhook-audit-blotter caveats](../webhook-audit-blotter/README.md#caveats) for the full picture.
