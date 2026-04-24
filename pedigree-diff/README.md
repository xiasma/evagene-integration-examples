# Pedigree diff

**Know what changed between two points in time, in one command.** Feed this two pedigree IDs (or two JSON snapshots you saved earlier) and it prints a human-readable change log: who was added, who was removed, what was corrected, what new diagnoses entered the family history.

This is an academic / research example of computing a structural, semantically-useful diff between two `PedigreeDetail` payloads. Pairs naturally with the [webhook-audit-blotter](../webhook-audit-blotter/) — the blotter captures that _something_ happened; this demo shows how to summarise _what changed_. It is a reference implementation, not a clinical record-review tool.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Integrators and developers** operating a webhook receiver who want a worked example of turning a stream of low-level `individual.created` / `individual.updated` events into a human-readable narrative.
- **Researchers** reconciling a pedigree import against the original submission, or diffing a synthetic dataset before and after a processing step.
- **Educators and students** studying how to diff structured domain objects with deterministic ordering and pluggable output formats.

## What Evagene surface this uses

- **REST API** — `GET /api/pedigrees/{pedigree_id}` (returns a `PedigreeDetail` object). Scope `read` is sufficient.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

The CLI can operate entirely offline against two saved JSON files, or fetch one or both sides live from the Evagene API. Mix and match freely — a common experimental pattern is to save a snapshot at one point and diff the live pedigree against it later to see what has changed.

## Prerequisites

1. An Evagene account and an API key with `read` scope — see [getting-started.md](../getting-started.md). The API key is only needed when one of the operands is a pedigree UUID.
2. Python 3.11 or later.

## Configuration

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no  | `https://evagene.net` | Override if you self-host. |
| `EVAGENE_API_KEY`  | only when an operand is a UUID | — | `evg_...` |

Both operands are positional CLI arguments, not environment variables, so a single session can diff many pedigrees without rewriting config. Copy `.env.example` to `.env` and fill in the key.

## Command-line contract

```
pedigree-diff <left> <right> [--format text|json|markdown] [--include-unchanged] [--since <ISO>]
```

- `<left>`, `<right>` — each can be a pedigree UUID (fetched live) or a path to a JSON file saved earlier. They can be combined freely: `UUID <-> UUID`, `UUID <-> file`, `file <-> file`, in any order.
- `--format` — `text` (default, ANSI-coloured when stdout is a TTY), `json` (machine-readable, deterministically ordered), `markdown` (for pasting into a referral letter).
- `--include-unchanged` — also list individuals who had no changes.
- `--since <ISO>` — restrict surfaced diagnoses to those dated at or after the given ISO-8601 date/timestamp. See *Caveats* below for what "date" means when a diagnosis lacks an explicit event date.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | No differences |
| `1` | Differences found |
| `64` | Usage error (missing or malformed arguments) |
| `69` | API unreachable or returned a non-2xx response |
| `70` | A snapshot file is missing, unreadable, or malformed |

## Run it

Only a Python implementation ships. `EVAGENE_API_KEY` is only required when one of the operands is a pedigree UUID; diffing two saved JSON files works offline.

### Run it in Python 3.11+

```bash
cd python

# Create and activate a virtual environment
python -m venv .venv

# Windows (cmd / PowerShell):
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

# Install the demo package + its dev tools (editable install so python -m <pkg> works)
pip install -e ".[dev]"

# Set your Evagene API key (one shell session; only needed for UUID operands)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
python -m pedigree_diff <left> <right>
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

## Expected output

Text mode, diffing the two fixtures:

```
Since 2026-04-15 (3 days):

+ Added: Mary Jones (maternal aunt, age 57)
  + Diagnosed with Ovarian Cancer, age 52

~ Updated: Emma Smith (proband)
  - Date of birth corrected: 1985-07-05 -> 1987-07-05

- Removed: John Smith (paternal uncle, was recorded as affected with Unknown Cancer)

+ Parent link added: Frank Jones -> Mary Jones
+ Parent link added: Susan Jones -> Mary Jones
- Parent link removed: George Smith -> John Smith
- Parent link removed: Helen Smith -> John Smith
```

The JSON and Markdown variants contain the same information — see `fixtures/expected-diff.json` and `fixtures/expected-diff.md`.

## Architecture

```
 CLI args + env ─►  Config ─┐
                            │
                   Snapshot sources (UUID or file path)
                            │
                   SnapshotLoader ──► EvageneClient (when UUID)
                            │         (over HttpGateway)
                            ▼
                   PedigreeSnapshot (x2)  — normalised value object
                            │
                            ▼
                   diff_engine  (pure)
                            │
                            ▼
                   RelationshipLabeler  (pure, "maternal aunt" etc.)
                            │
                            ▼
                   Formatter  (text / json / markdown)
                            │
                            ▼
                          stdout
```

- **config** — CLI + env into a validated `Config`.
- **http_gateway** — narrow HTTP abstraction; the tests fake it.
- **evagene_client** — knows the `GET /api/pedigrees/{id}` endpoint shape; returns a raw dict.
- **snapshot_loader** — dispatches UUID vs file path and normalises the raw `PedigreeDetail` into immutable value objects.
- **diff_engine** — pure: takes two snapshots, returns a structured `Diff`. Deterministic ordering so JSON output is byte-stable.
- **relationship_labeler** — pure: proband-centric relationship label ("maternal aunt", "first cousin").
- **formatters** — one module per output format, all implementing the same `Formatter` protocol.
- **app** — composition root; wires the pieces.

Every module has a single responsibility; no file reaches into another's internals.

## Fixtures

- `fixtures/pedigree-t0.json` — small BRCA family at time zero.
- `fixtures/pedigree-t1.json` — same family a few days later: a maternal aunt was added (with an ovarian-cancer diagnosis at 52), the proband's date of birth was corrected, and a paternal uncle was removed.
- `fixtures/expected-diff.txt` / `.json` / `.md` — golden outputs used by the formatter tests with a fixed "today" of 2026-04-18 so the "age N" lines stay stable across runs.

## Caveats

- This is an **academic / research example, not a clinical record-review tool**, not a medical device, and not fit for patient care.
- The tool reports observable differences between the two snapshots. Date-of-birth "corrections" and "removals" in the output reflect what changed in the recorded data, not necessarily what happened in reality — the comparison cannot distinguish a typo fix from a re-elicited history.
- Evagene's event model records birth and death dates on individuals and a list of diagnosis events per disease, but the `age_at_diagnosis` value and the associated event date are not always populated for every dataset. When a diagnosis lacks an explicit date, `--since` cannot filter it by year; the conservative choice is to include it. This is called out plainly because filtering silently would be worse than filtering loosely.
- Relationship labels are computed from the pedigree graph (parents, children, partners). Unusual or incomplete graphs fall back to "relative".
