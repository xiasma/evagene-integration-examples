# CanRisk bridge

**Hand a pedigree off to BOADICEA in one command.** Point this at an [Evagene](https://evagene.net) pedigree and it writes the `##CanRisk 2.0` file you need to upload to [canrisk.org](https://canrisk.org) — optionally opening the site in your browser so you can drop the file in immediately.

Built for the clinical geneticist who draws the family in Evagene and then runs the multi-gene panel (BOADICEA / BWA, PanelPRO profiles) on canrisk.org. No copy-and-paste, no manual exports — one command, a file on disk, and a working browser tab.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Clinical geneticists and genetic counsellors** running BOADICEA on canrisk.org as part of their familial-breast-cancer workup, who draw the pedigree in Evagene.
- **Research groups** processing an archive of pedigrees for BOADICEA scoring — the CLI is trivial to wrap in a shell loop or a batch job.
- **Integrators / developers** wanting a small, complete example of fetching a non-JSON payload from the Evagene API and writing it to disk, in Python, Node, .NET, or R.

## What Evagene surface this uses

- **REST API** — `GET /api/pedigrees/{pedigree_id}/risk/canrisk` with `Accept: text/tab-separated-values`. The response body is a plain-text `##CanRisk 2.0` file, not JSON.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scope `analyze` is sufficient.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account and an API key with `analyze` scope — see [getting-started.md](../getting-started.md).
2. A pedigree with enough structure for BOADICEA to evaluate — typically a proband plus first- and second-degree relatives with cancer ages of diagnosis recorded.
3. A recent runtime for the language you prefer — only one is needed.

## Configuration

Every language reads the same environment variables. Each language folder ships a `.env.example` (or `.Renviron.example` for R) you can copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

The pedigree ID is passed on the command line, so one shell session can export many pedigrees without rewriting config.

## Command-line contract

All four implementations accept the same invocation:

```
canrisk-bridge <pedigree-id> [--output-dir <dir>] [--open]
```

- `pedigree-id` — UUID of the pedigree to export.
- `--output-dir` — optional; directory to write into. Defaults to the current working directory.
- `--open` — optional; opens [https://canrisk.org](https://canrisk.org) in the default browser *after* the file has been saved.

The output filename is `evagene-canrisk-<first-8-of-pedigree-uuid>.txt`. On success the tool writes the saved file's absolute path to stdout on a single line and exits `0`.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | File saved successfully |
| `64` | Usage error (missing or malformed arguments) |
| `69` | API unreachable or returned a non-2xx response |
| `70` | Response body did not start with `##CanRisk 2.0` |

## One-line run per language

All four expect `EVAGENE_API_KEY` to be set in the environment (either exported or via `.env`). Work from the language-specific subfolder.

| Language | First-time setup | Run |
|---|---|---|
| **Python 3.11+** | `python -m venv .venv` · (activate) · `pip install -e .[dev]` | `python -m canrisk_bridge <pedigree-id>` |
| **Node 20+** | `npm install` | `npm start -- <pedigree-id>` |
| **.NET 8+** | `dotnet restore` | `dotnet run --project src/CanRiskBridge -- <pedigree-id>` |
| **R 4.3+** | `R -e 'install.packages(c("httr2","testthat"))'` | `Rscript inst/bin/canrisk-bridge.R <pedigree-id>` |

## Expected output

One line on stdout — the absolute path of the saved file:

```
/home/you/evagene-canrisk-a1cfe665.txt
```

The file itself starts with the `##CanRisk 2.0` header; upload it to [canrisk.org](https://canrisk.org) to run the BOADICEA assessment.

## Architecture (identical in every language)

```
 CLI args + env  ─┐
                  ├─►  Config (value object, validated)
 EVAGENE_API_KEY ─┘              │
                                 ▼
                         CanRiskClient ◄── HttpGateway (abstraction)
                                 │
                         (response text)
                                 ▼
                          OutputSink (file + optional browser)
```

- **Config** — immutable value object; validates that `EVAGENE_API_KEY` is present and that the pedigree ID is a UUID.
- **HttpGateway** — narrow abstraction (Protocol / interface) the tests fake.
- **CanRiskClient** — knows the Evagene endpoint and the `##CanRisk 2.0` guard; depends on `HttpGateway`.
- **OutputSink** — writes the payload to a file and optionally opens the browser. The browser launcher is also an injected abstraction so tests never shell out.
- **App** — composition root; wires the pieces.

## Test fixtures

A realistic `##CanRisk 2.0` file lives at `fixtures/sample-canrisk.txt` and is used by every language's unit tests. If Evagene changes the header wire-format, update this file and every language's test suite will point at the breakage.

## Caveats

- **BOADICEA is not bundled.** This demo exports the file; [canrisk.org](https://canrisk.org) runs the model. The academic terms of use on canrisk.org apply.
- The CanRisk 2.0 format is defined by the Centre for Cancer Genetic Epidemiology (Cambridge). Evagene produces it; this demo simply transports it.
- This is an example integration, not a validated clinical tool. Clinical governance applies.
