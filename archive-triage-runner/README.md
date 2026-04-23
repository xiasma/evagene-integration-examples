# Archive triage runner

**Point this at a folder of GEDCOM files and walk away with a defensible CSV of which families still warrant a genetics review.** For every `.ged` in the directory, the runner imports the pedigree into [Evagene](https://evagene.net), runs the NICE CG164 / NG101 familial-breast-cancer model, and appends one CSV row — `pedigree_id, proband_name, category, refer_for_genetics, triggers_matched_count, error`. A single clean command across an archive of hundreds of families.

Pairs with the **nice-traffic-light** demo: that one gives you a single-family green / amber / red; this one gives you the same decision at archive scale.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and configuring `EVAGENE_API_KEY` / `EVAGENE_BASE_URL`.

---

## Who this is for

- **Clinical geneticists** sweeping a historical archive after a policy or coding change — the CSV is a reproducible record of which families meet a NICE trigger today.
- **Genetic counsellors** prioritising a backlog of referrals by category before they open the pedigree editor.
- **Clinical informaticians** adding a nightly batch job that flags new incoming pedigrees against NICE so clinical review only sees the amber / red families.
- **Integrators / developers** who want a minimal end-to-end example of "create pedigree -> import GEDCOM -> run risk" against the Evagene REST API in Python or .NET.

## What Evagene surfaces this uses

- **REST API** — one pipeline per input file:
  - `POST /api/pedigrees` — create a pedigree with the filename stem as `display_name`.
  - `POST /api/pedigrees/{id}/import/gedcom` — JSON body `{"content": "<GEDCOM text>"}` (not `text/plain`).
  - `GET /api/pedigrees/{id}` — sanity-check that at least one individual has a non-zero `proband` flag.
  - `POST /api/pedigrees/{id}/risk/calculate` — body `{"model": "NICE"}`.
- **Authentication** — `X-API-Key: evg_...`. Scopes needed: **`write`** (to create and import pedigrees) and **`analyze`** (to run the NICE calculation). `read` is covered by `write`.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs).

## Prerequisites

1. An Evagene account and an API key with `write` + `analyze` scopes — see [../getting-started.md](../getting-started.md).
2. A folder of GEDCOM 5.5.1 files with at least one individual designated proband. Evagene reads the non-standard `1 _PROBAND <number>` tag (`1 _PROBAND 1` is the usual value); see `fixtures/sample.ged` for the shape.
3. A recent runtime for the language you prefer — only one is needed.

## Configuration

Each language folder ships a `.env.example` you can copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

The input folder, output file, and concurrency are passed on the command line.

## Command-line contract

Both implementations accept the same invocation:

```
archive-triage <input-dir> [--output <csv-file>] [--concurrency <N>]
```

- `input-dir` — required; scanned recursively for `*.ged`.
- `--output` — optional; CSV output file. Defaults to stdout.
- `--concurrency` — optional; in-flight pedigrees (default 4, max 32). Rate-limit kindness to the Evagene API.

### Exit codes

| Code | Meaning |
|---|---|
| `0`  | All files processed. The CSV contains a row per file — failures are captured as rows with a populated `error` column, not dropped. |
| `64` | Usage error (missing input directory, malformed flag, missing `EVAGENE_API_KEY`). |
| `69` | API unreachable for the whole run — not a single pedigree was created. |
| `70` | The input path is not a directory. |

## Run it

Both implementations expect `EVAGENE_API_KEY` to be set in the environment, and the input directory as the first positional argument.

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

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
python -m archive_triage ./archive --output triage.csv
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

### Run it in .NET 8+

```bash
cd dotnet

# Restore NuGet packages
dotnet restore

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
dotnet run --project src/ArchiveTriage -- ./archive --output triage.csv
```

Run the tests (optional):

```bash
dotnet test
```

## Expected output

A single CSV stream:

```
pedigree_id,proband_name,category,refer_for_genetics,triggers_matched_count,error
7c8d4d6a-...,Jane Smith,high,true,2,
9a1f3b28-...,Alice Brown,moderate,true,1,
b6d4e111-...,No Proband,,,0,no proband designated in GEDCOM — mark one with a _PROBAND 1 tag.
```

- `category` is one of `near_population`, `moderate`, `high` when the calculation succeeded; blank on failure.
- `refer_for_genetics` is `true` / `false` on success, blank on failure.
- `triggers_matched_count` is the length of the `nice_triggers` array Evagene returned (`0` on failure).
- `error` is empty on success and a short human-readable message on failure. A failure row still carries the `pedigree_id` of the partial pedigree so you can clean up or inspect it in the Evagene web UI.

A sample fixture lives at [`fixtures/sample.ged`](fixtures/sample.ged) and its expected CSV shape at [`fixtures/sample-output.csv`](fixtures/sample-output.csv) (UUIDs will differ).

## Architecture (identical in Python and .NET)

```
 ./archive/*.ged ──►  GedcomScanner ──►  (path, content) stream
                                                 │
 CLI args + env ─────►  Config                   ▼
                         │         ┌────►  TriageService  ◄── EvageneClient ◄── HttpGateway
                         └─────────┤              │
                                   │              ▼
                                   └────►  CsvWriter ──►  stdout or file
```

- **Config** — immutable value object; validates that `EVAGENE_API_KEY` is present and `--concurrency` is in range.
- **HttpGateway** — narrow abstraction (one method across GET / POST / DELETE) the tests fake.
- **EvageneClient** — one method per endpoint (`create_pedigree`, `import_gedcom`, `has_proband`, `calculate_nice`, `delete_pedigree`). Each a one-shot wrapper over one endpoint.
- **GedcomScanner** — walks the input directory and yields `(path, content)` pairs.
- **TriageService** — orchestrates the per-file pipeline, captures errors as `RowResult` values (no exceptions escape). A semaphore bounds in-flight work to `--concurrency`.
- **CsvWriter** — formats a `RowResult` stream into CSV and writes it to an injected sink (stdout or file).
- **App** — composition root; wires the pieces together.

Every file has one responsibility; every function has one level of abstraction.

## Rate-limit etiquette

`--concurrency` defaults to 4. Dial it up only if you know your API-key rate limits will absorb the load. The Evagene API returns HTTP 429 on rate-limit breaches; a 429 surfaces as an error row for the affected file rather than aborting the run, so you can re-run just the failing rows later.

## Caveats

- NICE CG164 / NG101 is a **screening triage tool** driven by family-history structure, not a continuous lifetime-risk estimate. For a continuous estimate, feed the pedigree to Tyrer-Cuzick (an IBIS-style approximation in Evagene) or export a `##CanRisk 2.0` file and upload it at [canrisk.org](https://canrisk.org) for the full BOADICEA assessment.
- The CSV is a **decision aid**, not the decision. Always review the amber / red families in the Evagene UI before triaging referrals.
- Failed rows leave a partial pedigree behind in your Evagene account (the runner captures the `pedigree_id` so you can clean up). For a periodic batch, either delete the partial pedigrees or re-use them — don't assume the archive starts clean every run.
- This is an example integration, not a validated clinical tool. Clinical governance applies.
