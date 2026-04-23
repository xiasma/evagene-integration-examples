# Longitudinal risk monitor

**A nightly sweep that tells you exactly which families' risk category changed today — and nothing else.** Point this at your [Evagene](https://evagene.net) account on a schedule and you get a quiet "nothing to do" report most days and a prioritised alert the moment a pedigree slips from GREEN to AMBER (or AMBER to RED) — typically because a newly added affected relative has tipped a NICE trigger. Pairs with the `webhook-audit-blotter` demo: webhooks are real-time, this is the end-of-day sanity sweep.

> **New to Evagene integrations?** Start with [../getting-started.md](../getting-started.md) — it covers registering at [evagene.net](https://evagene.net), minting an API key, and choosing pedigrees to monitor.

---

## Who this is for

- **Genetics service leads** wanting a daily inbox-sized summary of every family on their books.
- **Genetic counsellors** who look after a growing cohort and cannot manually re-run risk every time a family-history field changes.
- **Integrators** adding continuous risk-surveillance to an existing clinical dashboard, escalation system, or MDT prep routine.

## What Evagene surface this uses

- `GET /api/pedigrees` — list the caller's pedigrees.
- `POST /api/pedigrees/{pedigree_id}/risk/calculate` with body `{"model": "NICE"}` — recompute the NICE CG164 / NG101 category.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`; scope `analyze` is sufficient.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) / [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account and an API key with `analyze` scope — see [getting-started.md](../getting-started.md).
2. Python 3.11 or newer.
3. A scheduler of your choice (`cron`, `systemd-timer`, GitHub Actions, Windows Task Scheduler, Kubernetes `CronJob`, etc.). The tool itself is a single process; the cadence is your decision.

## Configuration

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EVAGENE_API_KEY` | yes (for `run` and `seed`) | — | `evg_...`, scope `analyze`. |
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | Override only for a self-hosted Evagene deployment. |
| `RISK_MONITOR_DB` | no | `./risk-monitor.db` | Where to keep the baseline + event log. |

Copy `python/.env.example` to `python/.env` and fill in the values, or export them in the shell your scheduler uses.

## Command-line contract

```
risk-monitor run     [--since <ISO-timestamp>] [--channel stdout|file|slack-webhook] [--channel-arg <arg>] [--dry-run]
risk-monitor history [--pedigree <uuid>] [--format text|json]
risk-monitor seed
```

| Subcommand | Purpose |
|---|---|
| `seed`    | First-use bootstrap. Writes a baseline row for every pedigree and emits **no** notifications. Run this once before scheduling `run`. |
| `run`     | Recompute NICE for every pedigree, diff against the store, emit a notification per pedigree whose category or trigger set has shifted. |
| `history` | Read-only view of recorded change events. |

### Flags on `run`

| Flag | Meaning |
|---|---|
| `--channel stdout` (default) | Print notifications to standard output. |
| `--channel file --channel-arg <path>` | Append notifications to a log file. |
| `--channel slack-webhook --channel-arg <url>` | `POST` an attachment-style payload to a Slack incoming webhook. |
| `--dry-run` | Compute and notify, but do **not** update the store. Useful while tuning thresholds. |
| `--since <ISO-timestamp>` | Echoed for audit; currently informational only. |

### Exit codes

| Code | `run` | `seed`, `history` |
|---|---|---|
| `0` | No changes detected this run. | Command completed. |
| `1` | One or more changes detected **and** notified. | (not used) |
| `64` | Usage error (missing/malformed arguments). | Usage error. |
| `69` | Evagene API unreachable or returned a non-2xx after retries. | Same. |

A `cron` line such as `0 2 * * * risk-monitor run --channel slack-webhook --channel-arg $SLACK_URL || true` runs at 02:00 every night; the `|| true` suppresses the non-zero exit code from a change-detection alert so the scheduler does not also email you.

## Run it

Only a Python implementation ships. `risk-monitor` has three subcommands: `seed` (once), `run` (every schedule tick), and `history`.

### Run it in Python 3.11+

```bash
cd python

# Create and activate a virtual environment
python -m venv .venv

# Windows (cmd / PowerShell):
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Set your Evagene API key and the SQLite baseline path (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
$env:RISK_MONITOR_DB = "./risk-monitor.db"
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...
export RISK_MONITOR_DB=./risk-monitor.db

# Bootstrap the baseline (run once)
python -m longitudinal_risk_monitor seed

# Recompute and notify (schedule this)
python -m longitudinal_risk_monitor run
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

## Expected output

On an unchanged run:

```
Checked 5 pedigree(s); 0 change(s) detected.
```

On a change:

```
Davies family (moderate-risk): NEAR_POPULATION -> MODERATE | added: Single first-degree relative with breast cancer <40.
Checked 5 pedigree(s); 1 change(s) detected.
```

## Architecture

```
 CLI argv + env ─► Config (RunConfig | HistoryConfig | SeedConfig)
                        │
                        ▼
                  Orchestrator ─────────────► Evagene REST API
                   │  │  │                      (GET /api/pedigrees,
                   │  │  │                       POST .../risk/calculate)
                   │  │  └──► Notifier (stdout | file | Slack webhook)
                   │  └──► Evaluator (pure; diff previous vs current)
                   └──► StateStore (SQLite baseline + event log)
```

Each module owns one responsibility; every collaborator is injected at the composition root (`app.py`). Rate-limit etiquette is built in: 200 ms between risk calls, and HTTP 429 responses are retried with exponential backoff + jitter up to three times before surfacing as an error.

## Caveats

- The NICE model is a **screening-triage** tool derived from family-history structure. It is not a continuous lifetime-risk estimate — use Tyrer-Cuzick (an IBIS-style approximation) or export to `##CanRisk 2.0` for BOADICEA at [canrisk.org](https://canrisk.org).
- This is an example integration, not a validated clinical tool — clinical governance applies.
- The SQLite baseline is your service's state. Back it up; a lost DB means the next `run` will treat every current category as "new" unless you re-seed.
