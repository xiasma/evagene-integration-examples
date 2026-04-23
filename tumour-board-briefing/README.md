# Tumour-board briefing

**One pedigree in, one print-ready PDF out.** Point this at an [Evagene](https://evagene.net) pedigree and it generates a self-contained briefing for an oncology MDT / tumour-board meeting: cover page, pedigree figure, six-model risk summary, the triggers and criteria each model flagged, and the clinical caveats that belong on every handout.

Designed for the clinician who is about to walk into a tumour board with nine cases on the slide deck and wants a defensible paper copy of each one without rebuilding the document by hand.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Oncology MDT convenors** assembling the paperwork for a weekly tumour board.
- **Clinical geneticists** preparing per-case briefings for a joint clinic or a referring MDT.
- **Genetic counsellors and specialist nurses** who need a printable handout to accompany a consultation.
- **Integrators / developers** wanting a working example of the Evagene REST API across several endpoints (pedigree detail, SVG export, risk calculation), composed into a real artefact.

## What Evagene surfaces this uses

- **REST API** —
  - `GET /api/pedigrees/{id}` for the pedigree detail block.
  - `GET /api/pedigrees/{id}/export.svg` for the rendered pedigree figure.
  - `POST /api/pedigrees/{id}/risk/calculate` once per model in the briefing (Claus, Couch, Frank, Manchester, NICE, Tyrer-Cuzick by default).
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scopes needed: `read` (for the pedigree) and `analyze` (for the risk calls).
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

## What the PDF contains

1. **Cover page** — pedigree name, proband (or counselee) name, date, brief family-history summary.
2. **Pedigree figure** — the SVG from Evagene, rendered for print.
3. **Risk summary table** — one row per model, with headline figure, notes, and any threshold flags (e.g. Manchester ≥20%).
4. **Triggers and criteria met** — per-model bullet points (e.g. the NICE high-risk triggers that fired, or the Manchester contributions).
5. **Caveats** — the non-negotiable clinical language for each model (Tyrer-Cuzick is an IBIS-style approximation; BOADICEA is not bundled; Manchester thresholds sit at ≥10% and ≥20%; and so on).
6. **Footer on every page** — generation timestamp, "Not a validated clinical tool — clinical governance applies", pedigree ID and page number.

## Prerequisites

1. An Evagene account and an API key with `read` and `analyze` scopes — see [getting-started.md](../getting-started.md).
2. A pedigree with meaningful family history for the breast / ovarian models to score (typically at least one first- or second-degree relative with breast or ovarian cancer).
3. Python 3.11 or newer.

## Configuration

Copy `python/.env.example` to `python/.env` and fill in your key:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | Override only when running against a non-default Evagene deployment. |
| `EVAGENE_API_KEY`  | yes | — | Your `evg_...` key. |

## Command-line contract

```
tumour-board-brief <pedigree-id> [--output <file.pdf>] [--models <comma-list>] [--counselee <ind-id>]
```

- `pedigree-id` — UUID of the pedigree.
- `--counselee` — optional; UUID of the target individual. Defaults to the pedigree's designated proband.
- `--output` — path to write the PDF to. Defaults to `./tumour-board-<short-uuid>-<yyyymmdd>.pdf`.
- `--models` — comma-separated list. Default: `claus,couch,frank,manchester,nice,tyrer_cuzick`.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | PDF rendered successfully. |
| `64` | Usage error (missing or malformed arguments). |
| `69` | Evagene API unreachable or returned a non-2xx response for a required call (pedigree detail or SVG). |
| `70` | Internal error, e.g. the output path could not be written. |

Per-model risk failures do **not** abort the briefing — the model's row is rendered as "not available" and the document still prints.

## Run it

Only a Python implementation ships: the PDF rendering pipeline (`reportlab` + `svglib`) is the load-bearing dependency, and duplicating it in another language would not add anything.

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
python -m tumour_board_briefing <pedigree-id>
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

## Architecture

```
 CLI args + env  ─┐
                  ├─►  Config (value object, validated)
 EVAGENE_API_KEY ─┘              │
                                 ▼
                    EvageneClient ◄── HttpGateway (abstraction)
                                 │
                                 ▼
                          Orchestrator  ───►  Risk aggregator (pure)
                                 │             Boilerplate (pure)
                                 ▼
                      BriefingDocument (value object)
                                 │
                                 ▼
                    PdfSink (abstraction) ◄── ReportLabPdfSink (platypus + svglib)
                                 │
                                 ▼
                              <file>.pdf
```

Every module has one responsibility. `PdfSink` exists so the orchestrator tests can assert the page-by-page sequence (cover → figure → table → triggers → caveats → finalise) without depending on reportlab internals. The one end-to-end test renders a real PDF and reads it back with `pypdf` to catch regressions in the rendering pipeline without pinning to exact byte output.

## Caveats

- **This is an example integration, not a validated clinical tool.** Clinical governance applies to any decision made from the briefing.
- **Tyrer-Cuzick** on this briefing is an IBIS-style approximation of the published Tyrer, Duffy & Cuzick 2004 model — not the official IBIS Breast Cancer Risk Evaluator. For a fully-validated run, export the pedigree as a `##CanRisk 2.0` pedigree file from Evagene and upload it at [canrisk.org](https://canrisk.org).
- **BOADICEA** is not bundled with Evagene. The CanRisk export is the official route.
- **Manchester thresholds** quoted on the briefing follow Evans et al. — BRCA1 / BRCA2 score ≥16 corresponds to ≈10% carrier probability; combined score ≥20 corresponds to ≈20%.
- **Pedigree figure rendering** uses svglib + reportlab's PNG renderer. Fonts referenced inside the SVG that are not installed on the rendering host will fall back to a default; the figure remains legible but the glyphs may not match the Evagene web UI exactly.
