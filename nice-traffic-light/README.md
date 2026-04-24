# NICE traffic light

**Family-history triage in one command.** Point this at an [Evagene](https://evagene.net) pedigree and it replies `GREEN`, `AMBER`, or `RED` — the NICE CG164 / NG101 familial-breast-cancer category for that family — along with the exact triggers that were matched.

This is an academic / research example: it shows how to call Evagene's risk endpoint from four languages and turn the NICE response into a traffic-light output with meaningful exit codes. It is not a clinical tool and must not be used to drive referral decisions.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Integrators and developers** wanting a small, complete example of calling the Evagene risk API cleanly from Python, Node, .NET, or R — the same composition reappears in every other demo in this repo.
- **Researchers** exploring how NICE's rule-based triage behaves across a synthetic or de-identified pedigree dataset — the exit codes make it trivial to script into a CSV summary.
- **Educators and students** teaching or learning how NICE CG164 / NG101 maps family-history structure to a green / amber / red category. The demo is a readable reference of the wire contract, not a decision-support tool.

## What NICE CG164 / NG101 actually says

NICE categorises familial breast-cancer risk into three bands, driven by family-history structure (not a continuous lifetime-risk estimate):

| Category | Lifetime risk | Traffic light | Category description (paraphrased) |
|---|---|---|---|
| `near_population` | <17% | **Green** | Population-level risk. |
| `moderate` | 17–30% | **Amber** | Moderate risk band. |
| `high` | ≥30% | **Red** | Meets a high-risk trigger in the NICE rules. |

Evagene evaluates the pedigree against the specific NICE triggers (age of diagnosis, number of affected relatives, bilateral disease, male breast cancer, etc.) and returns the category plus the list of triggers that fired. This demo surfaces both.

The authoritative reference for the rule text is NICE itself: see NICE CG164 (Familial breast cancer, 2013) and NG101 (updated 2023) for the full rules. This demo reproduces none of the NICE prose and offers no clinical interpretation of the categories — that remains the reader's responsibility.

## What Evagene surface this uses

- **REST API** — `POST /api/pedigrees/{pedigree_id}/risk/calculate` with body `{"model": "NICE"}`.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scope `analyze` is sufficient.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account and an API key with `analyze` scope — see [getting-started.md](../getting-started.md).
2. A pedigree with enough family history for NICE to meaningfully evaluate (typically at least one first- or second-degree relative affected with breast or ovarian cancer).
3. A recent runtime for the language you prefer — only one is needed.

## Configuration

Every language reads the same environment variables. Each language folder ships a `.env.example` (or `.Renviron.example` for R) you can copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

The pedigree ID and optional counselee ID are passed on the command line, not via env, so a single shell session can classify many pedigrees without rewriting config.

## Command-line contract

All four implementations accept the same invocation:

```
nice-traffic-light <pedigree-id> [--counselee <individual-id>]
```

- `pedigree-id` — UUID of the pedigree.
- `--counselee` — optional; UUID of the target individual. Defaults to the pedigree's proband.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Green — near-population risk |
| `1` | Amber — moderate risk |
| `2` | Red — high risk |
| `64` | Usage error (missing or malformed arguments) |
| `69` | API unreachable or returned a non-2xx response |
| `70` | API response did not match the NICE schema |

Designed so shell pipelines can branch cleanly — `nice-traffic-light <id> && echo "reassure" || echo "refer"`.

## Run it

All four implementations expect `EVAGENE_API_KEY` to be set in the environment, and the pedigree UUID as the first positional argument.

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

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
python -m nice_traffic_light <pedigree-id>
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

### Run it in Node 20+

```bash
cd node

# Install dependencies
npm install

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
npm start -- <pedigree-id>
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
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
dotnet run --project src/NiceTrafficLight -- <pedigree-id>
```

Run the tests (optional):

```bash
dotnet test
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
Rscript inst/bin/nice-traffic-light.R <pedigree-id>
```

Run the tests (optional):

```bash
Rscript -e 'loc <- Sys.getenv("R_LIBS_USER"); .libPaths(c(loc, .libPaths())); testthat::test_dir("tests/testthat")'
```

## Expected output

A single headline line (colour label + sentence), followed by the triggers that matched (if any):

```
AMBER  Moderate risk for Counselee, Moderate — refer if further history emerges.
  - Single first-degree relative with breast cancer <40.
```

```
RED    High risk for Counselee, High — refer for genetics assessment.
  - First-degree female relative with breast cancer <40.
  - Two or more first-degree relatives with breast cancer <50.
```

## Architecture (identical in every language)

```
 CLI args + env  ─┐
                  ├─►  Config (value object, validated)
 EVAGENE_API_KEY ─┘              │
                                 ▼
                         RiskApiClient ◄── HttpGateway (abstraction)
                                 │
                                 ▼
                         NiceClassifier (pure)
                                 │
                                 ▼
                       TrafficLightMapper (pure)
                                 │
                                 ▼
                           Presenter (sink)
```

- **Config** — immutable value object; validates that `EVAGENE_API_KEY` is present and that IDs are UUIDs.
- **HttpGateway** — narrow abstraction (Protocol / interface) the tests fake.
- **RiskApiClient** — knows the Evagene endpoint shape; depends on `HttpGateway`.
- **NiceClassifier** — pure transform from the API payload to a `NiceOutcome` domain object; no I/O, no globals.
- **TrafficLightMapper** — pure transform from `NiceOutcome` to a `TrafficLightReport`.
- **Presenter** — writes the report to an injected sink (stdout by default).
- **App** — composition root; wires the pieces. A handful of lines.

Every file has one responsibility. Every function has one level of abstraction. The same reading order works across all four languages.

## Test fixtures

The three canonical NICE responses (`near_population`, `moderate`, `high`) live at `fixtures/` and are used by every language's unit tests. This is the wire contract — if the Evagene server changes it, update these files and every language's test suite will point at the breakage.

## Caveats

- This is an **academic / research integration example**, not a clinical tool. It is not medical-grade, not validated for clinical use, and must not inform referral or care decisions.
- NICE CG164 / NG101 is a rule-based categorisation of family-history structure. It is not a continuous lifetime-risk estimate — for that use Tyrer-Cuzick (an IBIS-style approximation) or export the pedigree in `##CanRisk 2.0` format and upload it at [canrisk.org](https://canrisk.org) for the full BOADICEA assessment.
- The traffic light is a display convenience; the useful information is the category *plus* the triggers. Don't read anything into the colour in isolation.
