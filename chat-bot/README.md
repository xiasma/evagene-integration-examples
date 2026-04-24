# Chat-bot: Evagene in Slack and Microsoft Teams

**Paste a pedigree ID in chat and get the NICE category back in seconds.** `/evagene <pedigree-id>` in Slack (or `@Evagene <pedigree-id>` in Teams) replies in-channel with the pedigree's display name, the proband's name, a small SVG thumbnail link, and the NICE GREEN/AMBER/RED category plus the triggers that caused it.

This is an academic / research example of a signed-webhook chat surface in front of Evagene — full signature verification, rendering, and error handling in a small Node codebase. It is a reference implementation, not a clinical triage tool.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and finding a pedigree ID to try.

---

## Who this is for

- **Integrators and developers** standing up a signed-webhook chat surface in front of Evagene, with the full signature-verification, rendering, and error-handling pattern already written.
- **Researchers and educators** demonstrating Evagene output in a shared channel against a synthetic or de-identified dataset.
- **Students** studying the Slack slash-command + Teams outgoing-webhook contracts in one readable codebase.

## What Evagene surface this uses

- **REST API** — `GET /api/pedigrees/{id}/summary`, `GET /api/pedigrees/{id}/export.svg`, `POST /api/pedigrees/{id}/risk/calculate` with `model: NICE`.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs).

The bot never writes to Evagene. It only needs an API key with `read` and `analyze` scopes.

## Prerequisites

1. An Evagene account and an API key with `read` + `analyze` scopes — see [getting-started.md](../getting-started.md).
2. Node 20.10 or later.
3. A publicly reachable URL for the server (production) or a tunnel (`ngrok`, `cloudflared`) for local testing — Slack and Teams both need to reach you over HTTPS.
4. A Slack app (for the Slack surface) and/or an Outgoing Webhook registered in a Teams channel (for the Teams surface). You can enable one, the other, or both.

## Environment variables

Copy `node/.env.example` to `node/.env` and fill in the secrets.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EVAGENE_API_KEY` | yes | - | `evg_...` key with `read` + `analyze`. |
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | Override for self-hosted Evagene. |
| `SLACK_SIGNING_SECRET` | at least one | - | Slack app's signing secret, from **Basic Information -> App Credentials**. Omit to disable the Slack route. |
| `TEAMS_SIGNING_SECRET` | at least one | - | The HMAC key returned when you create the Teams Outgoing Webhook. Omit to disable the Teams route. |
| `PORT` | no | `3000` | TCP port the HTTP server binds. |

One of `SLACK_SIGNING_SECRET` or `TEAMS_SIGNING_SECRET` must be present.

## HTTP contract

| Method | Path | Behaviour |
|--------|------|-----------|
| `GET`  | `/healthz` | Returns `200 ok`. |
| `POST` | `/slack/commands/evagene` | Verifies `X-Slack-Signature` + `X-Slack-Request-Timestamp`, parses the slash-command body, fetches summary + SVG link + NICE, replies `200` with a Slack blocks payload. |
| `POST` | `/teams/evagene` | Verifies `Authorization: HMAC <base64>` over the raw body, parses the `text` field for a pedigree UUID, replies `200` with a Teams card payload. |

On any failure (bad signature, bad UUID, Evagene error) the bot replies `200` with a friendly in-channel error message rather than a 5xx, because Slack and Teams hide non-2xx responses from the user.

## Run it

Only a Node implementation ships: Slack and Teams both expect a single signed HTTP receiver and one language is enough. Startup prints:

```
Chat-bot listening on http://localhost:3000/
```

### Run it in Node 20+

```bash
cd node

# Install dependencies
npm install

# Set your API key, one of the signing secrets, and optional overrides
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
$env:SLACK_SIGNING_SECRET = "replace_with_slack_app_signing_secret"
$env:TEAMS_SIGNING_SECRET = "replace_with_teams_outgoing_webhook_hmac_token"
$env:PORT = "3000"
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...
export SLACK_SIGNING_SECRET=replace_with_slack_app_signing_secret
export TEAMS_SIGNING_SECRET=replace_with_teams_outgoing_webhook_hmac_token
export PORT=3000

# Run the server
npm start
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

## Installing the Slack slash command

1. **[https://api.slack.com/apps](https://api.slack.com/apps)** -> **Create New App** -> **From scratch**.
2. **Slash Commands** -> **Create New Command**:
   - Command: `/evagene`
   - Request URL: `https://your-server.example/slack/commands/evagene`
   - Short description: `Evagene pedigree triage`
   - Usage hint: `<pedigree-id>`
3. **Basic Information** -> copy the **Signing Secret** into `SLACK_SIGNING_SECRET`.
4. **Install App** to your workspace.
5. In any channel, type `/evagene 7c8d4d6a-2f3a-4c1e-9a0b-5c2d3e4f5a6b` (substitute a real pedigree UUID).

## Installing the Teams outgoing webhook

1. In the target Teams channel: **...** -> **Manage team** -> **Apps** -> **Create an outgoing webhook**.
2. **Callback URL**: `https://your-server.example/teams/evagene`.
3. **Name**: `Evagene`.
4. Copy the **HMAC token** that Teams returns on creation into `TEAMS_SIGNING_SECRET`.
5. In the channel: `@Evagene 7c8d4d6a-2f3a-4c1e-9a0b-5c2d3e4f5a6b`.

Teams outgoing-webhook documentation: [learn.microsoft.com](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-outgoing-webhook). Slack request-signing reference: [api.slack.com/authentication/verifying-requests-from-slack](https://api.slack.com/authentication/verifying-requests-from-slack).

## Expected output

Successful `/evagene <uuid>` in Slack produces a reply with:

- The pedigree display name and proband name as a header.
- A link to the pedigree's SVG export (Slack does not natively render inline SVG, so we link back to `https://evagene.net/api/pedigrees/{id}/export.svg` rather than trying to embed it).
- The NICE category (`GREEN`, `AMBER`, or `RED`) and a bulleted list of triggers.

In Teams, the bot returns an `MessageCard` with the same content and a `View pedigree` action button linking to the Evagene web UI.

## Architecture

```
  POST /slack/commands/evagene          POST /teams/evagene
        |                                      |
        v                                      v
  slackVerifier (v0 HMAC)              teamsVerifier (HMAC)
        |                                      |
        `------------.   .---------------------'
                     v   v
                  handlers
                     |
                     v
                evageneClient --> httpGateway --> fetch
                     |
          summary + svg url + NICE result
                     |
         .-----------+------------.
         v                        v
     renderSlack              renderTeams
         |                        |
         v                        v
   Slack blocks JSON       Teams card JSON
```

One function per module, one responsibility per function. `app.ts` is the only place concretes are bound to abstractions.

## Smoke test (no real Slack or Teams workspace needed)

`test/server.test.ts` boots the Express server on an ephemeral port and posts a request with a correctly computed signature for each platform. That exercise is identical to what a real Slack / Teams delivery looks like, so a green test suite means the signed pipeline works end-to-end.

To hit a live server with a synthesised Slack request:

```bash
export SLACK_SIGNING_SECRET=shhh
export BODY="token=t&team_id=T&channel_id=C&user_id=U&command=%2Fevagene&text=7c8d4d6a-2f3a-4c1e-9a0b-5c2d3e4f5a6b"
export TS=$(date +%s)
BASE="v0:${TS}:${BODY}"
SIG=$(printf %s "$BASE" | openssl dgst -sha256 -hmac "$SLACK_SIGNING_SECRET" -r | awk '{print $1}')
curl -i -X POST http://localhost:3000/slack/commands/evagene \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Slack-Request-Timestamp: $TS" \
  -H "X-Slack-Signature: v0=$SIG" \
  --data-binary "$BODY"
```

## Caveats

- This is an **academic / research example, not a validated clinical tool**, not a medical device, and not fit for patient care. Use it with synthetic or de-identified pedigrees — not live patient data in a real channel.
- **SVG rendering is asymmetric.** Slack does not render SVG inline, so we link to the pedigree's `export.svg`. Teams cards *could* render a base64-embedded PNG, but we link instead, keeping the bot dependency-free. If you need an inline thumbnail, convert SVG to PNG in a separate microservice — do not add `sharp` / `librsvg` into this bot.
- **The bot would expose pedigree names and NICE categories in a chat channel.** Channel membership is your access-control boundary. Review whether that matches your information-governance policy before experimenting even with synthetic data.
- **NICE CG164 / NG101 classification** is a rule-based categorisation, not a diagnostic. The GREEN / AMBER / RED output is illustrative, not a decision.
