# BayesMendel comparator

**Same pedigree, three classical cancer-risk models, one side-by-side table.** Point this at an [Evagene](https://evagene.net) pedigree and it prints BRCAPRO, MMRpro, and PancPRO carrier probabilities and future-risk projections in a single comparison you can read in five seconds. The models live in the BayesMendel R library; Evagene runs them behind its REST API, so this demo stays a thin client.

Useful when someone on an MDT asks "what does *BRCAPRO* say here — and does it agree with MMRpro?" and you want a reproducible answer rather than three separate UI trips.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Medical oncologists** presenting a family at an MDT and needing the BayesMendel numbers in one place alongside the family-history triage.
- **Clinical geneticists** comparing model outputs when no single model fits a mixed-cancer family cleanly, or when writing up a case for audit.
- **Research genetic counsellors** fanning out model comparisons across a cohort and piping the CSV into a spreadsheet or notebook.
- **R users** (and Python developers) who want a minimal, readable example of calling Evagene's `risk/calculate` endpoint for the BayesMendel models.

## What the three models actually compute

Each model returns the posterior probability that the proband (or chosen counselee) carries a mutation in the genes it covers, plus projected cancer risk by age.

| Model | Cancers evaluated | Genes modelled | Reference |
|---|---|---|---|
| **BRCAPRO** | Breast, ovarian | BRCA1, BRCA2 | Parmigiani et al., *Am J Hum Genet* 1998 |
| **MMRpro** | Colorectal, endometrial | MLH1, MSH2, MSH6 | Chen et al., *JAMA* 2006 |
| **PancPRO** | Pancreatic | Aggregate susceptibility | Wang et al., *J Clin Oncol* 2007 |

All three are implemented in the [BayesMendel](https://projects.iq.harvard.edu/bayesmendel) R library by the Parmigiani lab. Evagene ships an R sidecar that executes the library and exposes it over the standard `POST /api/pedigrees/{id}/risk/calculate` endpoint, so this demo is a plain HTTP client — no R statistics code of its own.

## What Evagene surface this uses

- **REST API** — `POST /api/pedigrees/{pedigree_id}/risk/calculate` with body `{"model": "BRCAPRO"}`, `{"model": "MMRpro"}`, `{"model": "PancPRO"}`. One call per model, three calls total.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scope `analyze` is sufficient.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

Under the bonnet, Evagene proxies each request to its R sidecar which runs the BayesMendel library and shapes the response. For hosted users (`https://evagene.net`) the sidecar is always online; no setup is required on the caller's side.

## Prerequisites

1. An Evagene account and an API key with `analyze` scope — see [getting-started.md](../getting-started.md).
2. A pedigree with a designated proband. At least one first- or second-degree relative affected with a breast/ovarian/colorectal/endometrial/pancreatic cancer makes the comparison interesting; an otherwise-empty pedigree will return near-population priors for every model.
3. A recent runtime for the language you prefer — only one is needed.

## Configuration

Every language reads the same environment variables. Each language folder ships a `.env.example` (or `.Renviron.example` for R) you can copy and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | —                     | `evg_...` |

## Command-line contract

Both implementations accept the same invocation:

```
bayesmendel-comparator <pedigree-id> [--counselee <individual-id>] [--format table|csv|json]
```

- `pedigree-id` — UUID of the pedigree (required).
- `--counselee` — UUID of the target individual; defaults to the pedigree's proband.
- `--format` — output shape; one of `table` (default), `csv`, or `json`.

### Exit codes

| Code | Meaning |
|---|---|
| `0`  | All three models returned successfully. |
| `64` | Usage error (missing or malformed arguments). |
| `69` | At least one model call failed (HTTP error, sidecar down, pedigree lacks a proband, etc.). |
| `70` | A model's response did not match the BayesMendel schema. |

Designed so a shell pipeline can fan out across an archive and report only the families where every model succeeded.

## Run it

Both implementations expect `EVAGENE_API_KEY` to be set in the environment, and the pedigree UUID as the first positional argument.

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
python -m bayesmendel_comparator <pedigree-id>
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

### Run it in R 4.3+

```bash
cd r

# Install dependencies (user library)
Rscript -e 'loc <- Sys.getenv("R_LIBS_USER"); if (!dir.exists(loc)) dir.create(loc, recursive = TRUE, showWarnings = FALSE); .libPaths(c(loc, .libPaths())); install.packages(c("httr2", "jsonlite", "testthat"), repos = "https://cloud.r-project.org")'

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
Rscript inst/bin/bayesmendel-comparator.R <pedigree-id>
```

Run the tests (optional):

```bash
Rscript -e 'loc <- Sys.getenv("R_LIBS_USER"); .libPaths(c(loc, .libPaths())); testthat::test_dir("tests/testthat")'
```

## Expected output

The `table` format prints one row per model with carrier probabilities and the highest projected lifetime risk (columns are truncated here for readability):

```
Model    Counselee  Any carrier  Pr(BRCA1 mutation)  Pr(BRCA2 mutation)  ...  Pr(MLH1 mutation)  Pr(MSH2 mutation)  Pr(MSH6)  Lifetime risk @max-age
BRCAPRO  Emma       56.04%       42.39%              13.38%              ...  -                  -                  -         Breast Ca Risk 38.48%; Ovarian Ca Risk 28.46%
MMRpro   Emma        0.09%       -                   -                   ...   0.04%              0.04%              0.02%    Colorectal Ca Risk 3.26%; Endometrial Ca Risk 1.93%
PancPRO  Emma        0.54%       -                   -                   ...  -                  -                  -         Pancreatic Ca Risk 1.38%
```

The gene-probability columns are the union of every `carrier_probabilities` key the three responses populate, in first-seen order. Models that do not populate a given column show `-`. The lifetime-risk cell picks the oldest age in the response's `future_risks` array and renders each cancer type as a percentage.

The `csv` format emits the same content as a header plus three rows, suitable for piping into a spreadsheet. The `json` format emits an object with `rows` and `columns` — handy for downstream tooling.

## Architecture (identical in both languages)

```
  CLI args + env
        │
        ▼
     Config ──────────────────────────────┐
        │                                  │
        ▼                                  │
  RiskApiClient.calculate(model)  ◄── HttpGateway (abstraction)
        │ (three calls, one per model)
        ▼
  ModelRegistry (declares BRCAPRO / MMRpro / PancPRO and how each contributes)
        │
        ▼
  comparison_builder (pure)  →  ComparisonTable (rows × columns)
        │
        ▼
  Presenter (table | csv | json)  →  stdout
```

- **Config** — immutable value object; validates `EVAGENE_API_KEY`, pedigree/counselee UUIDs, and `--format`.
- **HttpGateway** — narrow abstraction the tests fake; production code uses `httr2` (R) or `httpx` (Python).
- **RiskApiClient.calculate(model)** — one method parameterised by model name; issues the POST and validates the envelope.
- **ModelRegistry** — the single place that declares which three models this demo compares.
- **comparison_builder** — pure transform: three `RiskResult` payloads in, one `ComparisonTable` out.
- **Presenters** — one per `--format` choice; each writes to an injected sink.
- **App** — composition root; wires the pieces and maps errors to exit codes.

## Test fixtures

`fixtures/sample-brcapro.json`, `sample-mmrpro.json`, and `sample-pancpro.json` capture realistic `RiskResult` payloads for each model. They are used by both languages' unit tests. If Evagene changes the response shape, update these three files and every language's test suite will point at the breakage.

## Caveats

- BRCAPRO, MMRpro, and PancPRO are **mutation-carrier probability models**, not deterministic diagnoses. A high posterior is a trigger for genetic testing — it is not testing. Clinical decisions should go through the usual multidisciplinary governance.
- The models were trained on specific founder populations (non-Ashkenazi is the default; set `allef_type` in the request body for Ashkenazi or Italian priors) and on cancer types present at the time of publication. They do not incorporate PALB2, ATM, CHEK2, PMS2, or polygenic risk scores — use BOADICEA (export the CanRisk file from Evagene and upload at [canrisk.org](https://canrisk.org)) if you need those.
- Each model only scores the cancer types it was built for. Families with mixed phenotypes will look reassuring under one model and alarming under another — that is why the comparison exists, not because the models disagree on biology.
- Attributions: BRCAPRO (Parmigiani, Berry, Aguilar, *Am J Hum Genet* 1998); MMRpro (Chen et al., *JAMA* 2006); PancPRO (Wang et al., *J Clin Oncol* 2007). The underlying library is [BayesMendel](https://projects.iq.harvard.edu/bayesmendel).
- This is an example integration, not a validated clinical tool. Clinical governance applies.
