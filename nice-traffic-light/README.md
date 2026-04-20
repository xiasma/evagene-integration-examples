# NICE traffic light

**Family-history triage in one command.** Point this at an [Evagene](https://evagene.net) pedigree and it replies `GREEN`, `AMBER`, or `RED` — the NICE CG164 / NG101 familial-breast-cancer category for that family — along with the exact triggers that were matched.

Built for the GP, genetic nurse, or clinical geneticist who needs a defensible answer to *"does this family warrant a genetics referral?"* without opening the web UI every time. Exit codes make it trivial to pipe into a referral-letter generator, drop into a clinic dashboard, or fan out across an archive of pedigrees and flag only the families that need a human look.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **GPs / primary-care doctors** running a family-history triage at the point of referral — the NICE categories map directly onto the "refer / routine surveillance / reassure" decision.
- **Genetic nurses and counsellors** processing a batch of incoming referrals and wanting to prioritise the high-risk families first.
- **Clinical geneticists** sanity-checking an archive of pedigrees after a policy or coding change — the tool gives you a reproducible green/amber/red per family, scriptable into a CSV.
- **Integrators / developers** wanting a small, complete example of calling the Evagene risk API cleanly from Python, Node, .NET, or R.

## What NICE CG164 / NG101 actually says

NICE categorises familial breast-cancer risk into three bands, driven by family-history structure (not a continuous lifetime-risk estimate):

| Category | Lifetime risk | Traffic light | Clinical action (paraphrased) |
|---|---|---|---|
| `near_population` | <17% | **Green** | No enhanced surveillance; reassure and discharge to primary care. |
| `moderate` | 17–30% | **Amber** | Routine surveillance and specialist advice; refer if further significant history emerges. |
| `high` | ≥30% | **Red** | Meets a high-risk trigger — refer for genetics assessment. |

Evagene evaluates the pedigree against the specific NICE triggers (age of diagnosis, number of affected relatives, bilateral disease, male breast cancer, etc.) and returns the category plus the list of triggers that fired. This demo surfaces both.

The official guidance is the clinical source of truth: see NICE CG164 (Familial breast cancer, 2013) and NG101 (updated 2023) for the full rules.

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

## One-line run per language

All four expect `EVAGENE_API_KEY` to be set in the environment (either exported or via `.env`). Work from the language-specific subfolder.

| Language | First-time setup | Run |
|---|---|---|
| **Python 3.11+** | `python -m venv .venv` · (activate) · `pip install -e .[dev]` | `python -m nice_traffic_light <pedigree-id>` |
| **Node 20+** | `npm install` | `npm start -- <pedigree-id>` |
| **.NET 8+** | `dotnet restore` | `dotnet run --project src/NiceTrafficLight -- <pedigree-id>` |
| **R 4.3+** | `R -e 'install.packages(c("httr2","jsonlite","cli","testthat"))'` | `Rscript inst/bin/nice-traffic-light.R <pedigree-id>` |

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

- NICE CG164 / NG101 is a **screening triage tool** that Evagene implements from family-history structure. It is not a continuous lifetime-risk estimate — for that use Tyrer-Cuzick (an IBIS-style approximation) or export the pedigree in `##CanRisk 2.0` format and upload it at [canrisk.org](https://canrisk.org) for the full BOADICEA assessment.
- The traffic light is a UX convenience; the clinical decision is the category *plus* the triggers. Don't use the colour in isolation.
- This is an example integration, not a validated clinical tool. Clinical governance applies.
