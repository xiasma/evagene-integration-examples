# Tumour-board briefing

**One pedigree in, one print-ready PDF out.** Point this at an [Evagene](https://evagene.net) pedigree and it generates a self-contained PDF: cover page, pedigree figure, six-model risk summary, the triggers and criteria each model flagged, plus the model-specific caveats that go with each figure.

This is an academic / research example of composing several Evagene REST endpoints (pedigree detail, SVG export, risk calculation per model) into a single document artefact. It is not a clinical tool and must not be used to produce real handouts for a tumour-board or MDT meeting.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Integrators and developers** wanting a working example of the Evagene REST API across several endpoints (pedigree detail, SVG export, risk calculation), composed into a real document artefact.
- **Researchers** exploring how six different risk models score the same synthetic pedigree, side-by-side, as a read-only PDF.
- **Educators** preparing teaching material that shows how the model outputs map onto a single case study — with the output clearly marked as example / academic material, never as a real briefing.

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
5. **Caveats** — the model-specific caveats for each figure (Tyrer-Cuzick is an IBIS-style approximation; BOADICEA is not bundled; Manchester thresholds sit at ≥10% and ≥20%; and so on), and the "academic / research example, not a validated clinical tool" disclaimer.
6. **Footer on every page** — generation timestamp, "Academic / research example — not a validated clinical tool", pedigree ID and page number.

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

**Note on PDF rendering:** this demo embeds the Evagene SVG pedigree directly as a ReportLab `Drawing` (via `svglib`) — no Cairo, no ImageMagick, no separate raster pipeline. `svglib` falls back to Helvetica when an SVG font face isn't available locally, so the figure glyphs in the generated PDF may not be pixel-identical to the Evagene web UI — a purely cosmetic difference.

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

- **This is an academic / research example, not a validated clinical tool, not a medical device, and not fit for patient care.** The generated PDF is illustrative material — do not present it as a real tumour-board or MDT briefing, and do not use it to inform any clinical decision.
- **Tyrer-Cuzick** on this briefing is an IBIS-style approximation of the published Tyrer, Duffy & Cuzick 2004 model — not the official IBIS Breast Cancer Risk Evaluator. For a fully-validated run, export the pedigree as a `##CanRisk 2.0` pedigree file from Evagene and upload it at [canrisk.org](https://canrisk.org).
- **BOADICEA** is not bundled with Evagene. The CanRisk export is the official route.
- **Manchester thresholds** quoted on the briefing follow Evans et al. — BRCA1 / BRCA2 score ≥16 corresponds to ≈10% carrier probability; combined score ≥20 corresponds to ≈20%.
- **Pedigree figure rendering** uses svglib + reportlab's PNG renderer. Fonts referenced inside the SVG that are not installed on the rendering host will fall back to a default; the figure remains legible but the glyphs may not match the Evagene web UI exactly.
