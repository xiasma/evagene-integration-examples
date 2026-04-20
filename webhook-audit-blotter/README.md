# Webhook audit blotter

**A tamper-evident record of every pedigree change.** Register this server as a webhook endpoint in [Evagene](https://evagene.net), and every `pedigree.*`, `individual.*`, `analysis.completed`, and `import.completed` event is HMAC-verified and written into a SQLite log whose rows are hash-chained — any later tampering with a row breaks the chain and is reported by a single `GET /events/verify` call.

Designed for compliance, medical-records, and clinical-audit teams who need a defensible answer to *"show me, in order, every change made to this pedigree, and prove the log has not been edited."*

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Compliance officers** needing an immutable record of pedigree and analysis activity for audit trails (ISO 27001, HIPAA, UK DSPT).
- **Clinical-records teams** reconciling Evagene activity against a master patient record.
- **Security engineers** standing up a webhook receiver with the recommended HMAC + constant-time verification pattern, without reinventing the boilerplate.
- **Integrators / developers** wanting a complete, minimal example of a webhook receiver in Node, .NET, and Python that all share the same architecture.

## What Evagene surface this uses

- **Webhooks** — HMAC-SHA256-signed outbound `POST`s from Evagene to this server. Register at `POST /api/webhooks`.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

Evagene sends each delivery with:

- `X-Evagene-Event` — the event name (`pedigree.updated`, `analysis.completed`, etc.).
- `X-Evagene-Signature-256` — `sha256=` followed by a hex HMAC-SHA256 of the raw request body, computed with the per-webhook secret returned at webhook-creation time.
- `X-Evagene-Delivery` — a per-delivery UUID (logged for cross-reference with the Evagene dashboard).

Events handled: `pedigree.created`, `pedigree.updated`, `pedigree.deleted`, `individual.created`, `individual.updated`, `individual.deleted`, `analysis.completed`, `import.completed`.

## Prerequisites

1. An Evagene account — see [getting-started.md](../getting-started.md).
2. A publicly reachable URL (or a tunnel — `ngrok`, `cloudflared`) so Evagene can reach the server. Evagene requires HTTPS in production.
3. A webhook registered against your URL via `POST /api/webhooks`. The response returns the secret *once* — paste it into this server's `EVAGENE_WEBHOOK_SECRET`.
4. A recent runtime for the language you prefer.

### Registering the webhook

```bash
curl -X POST https://evagene.net/api/webhooks \
  -H "X-API-Key: $EVAGENE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://your-server.example/webhook",
        "events": ["pedigree.created","pedigree.updated","pedigree.deleted",
                   "individual.created","individual.updated","individual.deleted",
                   "analysis.completed","import.completed"],
        "description": "Audit blotter"
      }'
```

The response contains the secret in `secret_last4` on the **first call only** (see the API reference). Store it somewhere safe and export it as `EVAGENE_WEBHOOK_SECRET` before starting this server.

## Configuration

Every language reads the same environment variables. Each language folder ships a `.env.example` you can copy to `.env`.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EVAGENE_WEBHOOK_SECRET` | yes | — | The secret returned when the webhook was created. |
| `PORT`                   | no  | `4000` | TCP port the HTTP server binds. |
| `SQLITE_PATH`            | no  | `./blotter.db` | File path for the audit log. Parent directory must exist. |

## HTTP contract

| Method | Path             | Behaviour |
|--------|------------------|-----------|
| `POST` | `/webhook`       | Verifies `X-Evagene-Signature-256` against the raw body, persists the event, returns `204`. Bad signature → `401`. Non-JSON body → `400`. |
| `GET`  | `/events`        | Returns the audit log as JSON Lines (`application/x-ndjson`). Paginated via `?limit=100&offset=0`. |
| `GET`  | `/events/verify` | Recomputes the hash chain from row 1. Returns `{"ok": true, "break_at": null}` or `{"ok": false, "break_at": <row-id>}`. |

### Hash-chain construction

Each row stores:

```
received_at | event_type | body | prev_hash | row_hash
```

`row_hash = SHA-256( prev_hash || received_at || event_type || body )` as UTF-8 concatenation, hex-encoded. The first row's `prev_hash` is the empty string. Editing any field of any row later will cause that row's `row_hash` — and every row after it — to disagree with the recomputed chain; `GET /events/verify` returns the ID of the first broken row.

## One-line run per language

Work from the language-specific subfolder.

| Language | First-time setup | Run |
|---|---|---|
| **Node 20+**    | `npm install` | `npm start` |
| **.NET 8+**     | `dotnet restore` | `dotnet run --project src/WebhookAuditBlotter` |
| **Python 3.11+** | `python -m venv .venv` · (activate) · `pip install -e .[dev]` | `python -m webhook_audit_blotter` |

All three print a single line on startup:

```
Webhook audit blotter listening on http://localhost:4000/
```

## Smoke test (no real Evagene delivery needed)

Synthesize a signed delivery locally:

```bash
export EVAGENE_WEBHOOK_SECRET=shhh
BODY="$(cat fixtures/sample-delivery.json)"
SIG=$(printf %s "$BODY" | openssl dgst -sha256 -hmac "$EVAGENE_WEBHOOK_SECRET" -r | awk '{print $1}')
curl -i -X POST http://localhost:4000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Evagene-Event: pedigree.updated" \
  -H "X-Evagene-Signature-256: sha256=$SIG" \
  --data-binary "$BODY"
curl -s http://localhost:4000/events
curl -s http://localhost:4000/events/verify
```

Expected: `204` on `/webhook`, a single JSON-lines row from `/events`, and `{"ok":true,"break_at":null}` from `/events/verify`.

## Architecture (identical in every language)

```
  POST /webhook
       │
       ▼
  SignatureVerifier (pure, constant-time compare)
       │  ok
       ▼
  WebhookHandler ── depends on ──► EventStore (SQLite, hash-chained rows)
       │
       ▼
  204 No Content
```

- **Config** — immutable value object; validates `EVAGENE_WEBHOOK_SECRET` is present and `PORT` is in range.
- **SignatureVerifier** — single function: raw body bytes + hex signature + secret → bool. Uses the platform's constant-time comparison (`timingSafeEqual` / `CryptographicOperations.FixedTimeEquals` / `hmac.compare_digest`).
- **EventStore** — SQLite access: `append(event)`, `list(limit, offset)`, `verify_chain()`. Prepared statements only. The chain is recomputed from stored rows — it does not trust the stored `row_hash` until it has been re-derived.
- **WebhookHandler** — orchestrator: verify → persist → respond. No framework types.
- **Server** — framework-specific (Express / ASP.NET Core / Flask) thin wiring layer.
- **App** — composition root; wires the pieces.

## Caveats

- This is a **single-node** demo. A production audit log that survives crashes, horizontal scaling, and insider threat needs a durable append-only store (WORM storage, external timestamping, or a transparency-log backend). Don't ship the SQLite file as-is to production.
- The hash chain detects tampering *after the fact* — it does not prevent it. An attacker with write access to the database can recompute every row's hash. For strong guarantees, periodically anchor the latest `row_hash` in a separate, independently-controlled system (a signed email digest, another organisation's audit feed, a public transparency log).
- This demo records the raw signed body. Depending on what events you subscribe to, that may include patient-identifying information — apply the same data-handling controls you would to any other clinical audit artefact.
- This is an example integration, not a validated clinical-governance tool. Clinical and regulatory governance applies.
