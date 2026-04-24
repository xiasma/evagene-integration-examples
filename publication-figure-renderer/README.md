# Publication figure renderer

**A pedigree you can paste straight into a paper.** Point this at an [Evagene](https://evagene.net) pedigree and one command writes out a print-quality SVG, optionally with every display name replaced by the standard clinical-genetics convention (`I-1`, `II-3`, `III-2`) so the figure is ready for open publication.

This is an academic / research example: it is aimed squarely at research write-up, methods papers, and teaching material. Pull a figure for a paper, de-identify it, paste it in.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Researchers** writing up a family (synthetic, consented, or de-identified) for a journal, needing the pedigree at print resolution with generation-number labels rather than display names.
- **Cohort-paper authors** fanning the tool out across a batch of pedigrees and wanting a single reproducible command per figure.
- **Educators** producing teaching figures that follow the standard `I-1 / II-3 / III-2` convention.
- **Developers and integrators** wanting a minimal example of the Evagene SVG-export endpoint and a safe way to rewrite the resulting XML without regex.

## What this demo does

1. Downloads the pedigree as an SVG from `GET /api/pedigrees/{id}/export.svg`.
2. If `--deidentify` is set, fetches the pedigree detail from `GET /api/pedigrees/{id}` to map each individual's ID and generation onto a publication-safe label.
3. Parses the SVG through a proper XML parser (no regex), replaces the display-name text in each `<text>` element, and writes the result to disk.

Label styles:

- `generation-number` (default) — `I-1`, `I-2`, `II-1`, `II-3`, etc., per clinical-genetics convention. Individuals missing a generation fall back to `?-1`, `?-2`, ...
- `initials` — `RS` for "Robert Smith".
- `off` — removes the label text entirely; useful when the figure caption already carries the labels.

## What Evagene surface this uses

- **REST API** — `GET /api/pedigrees/{id}/export.svg` for the figure and `GET /api/pedigrees/{id}` for the individual metadata (only when `--deidentify` is set).
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scope `read` is sufficient.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account and an API key with `read` scope — see [getting-started.md](../getting-started.md).
2. A pedigree ID for a family you own. Any realistic pedigree will do; generation numbers are taken from each individual's `generation` field.
3. A recent runtime for the language you prefer — R 4.3+ or Python 3.11+.

## Configuration

Both languages read the same environment variables. Each language folder ships an example file you can copy and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

## Command-line contract

Both implementations accept the same invocation:

```
pubfig <pedigree-id> --output <file.svg> [--deidentify] [--label-style initials|generation-number|off] [--width <px>] [--height <px>]
```

- `pedigree-id` — UUID of the pedigree (required).
- `--output` — path to write the SVG file to (required).
- `--deidentify` — replace display names according to `--label-style`.
- `--label-style` — defaults to `generation-number` and only matters when `--deidentify` is set.
- `--width`, `--height` — optional positive-integer overrides for the SVG root `width` / `height` attributes (the `viewBox` is left untouched so the figure scales cleanly).

### Exit codes

| Code | Meaning |
|---|---|
| `0`  | Figure written successfully. |
| `64` | Usage error (missing or malformed arguments). |
| `69` | API unreachable or returned a non-2xx response. |
| `70` | SVG returned by the API could not be parsed. |

## Run it

Both implementations expect `EVAGENE_API_KEY` to be set in the environment, the pedigree UUID as the first positional argument, and an explicit `--output` path.

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
python -m publication_figure_renderer <pedigree-id> --output fig.svg --deidentify
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
Rscript -e 'loc <- Sys.getenv("R_LIBS_USER"); if (!dir.exists(loc)) dir.create(loc, recursive = TRUE, showWarnings = FALSE); .libPaths(c(loc, .libPaths())); install.packages(c("httr2", "jsonlite", "xml2", "testthat"), repos = "https://cloud.r-project.org")'

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
Rscript inst/bin/pubfig.R <pedigree-id> --output fig.svg --deidentify
```

Run the tests (optional):

```bash
Rscript -e 'loc <- Sys.getenv("R_LIBS_USER"); .libPaths(c(loc, .libPaths())); testthat::test_dir("tests/testthat")'
```

## Expected output

```
$ pubfig 7c8d4d6a-... --output fig.svg --deidentify
Wrote fig.svg
```

The file starts with a standard XML preamble followed by an `<svg xmlns="http://www.w3.org/2000/svg">` root. With `--deidentify` and the default label style, every `<text>` element contains a generation-number label (`I-1`, `II-3`, etc.) rather than the patient's display name.

## Architecture (identical in both languages)

```
 CLI args + env  ─┐
                  ├─►  Config (value object, validated)
 EVAGENE_API_KEY ─┘              │
                                 ▼
                         EvageneClient ◄── HttpGateway (abstraction)
                                 │  fetch_pedigree_svg
                                 │  fetch_pedigree_detail (only with --deidentify)
                                 ▼
                         LabelMapper (pure)  ── individual_id → new label
                                 │
                                 ▼
                       SvgDeidentifier (pure, xml2 / lxml — no regex)
                                 │
                                 ▼
                           OutputWriter (disk)
```

- **Config** — immutable value object; validates that `EVAGENE_API_KEY` is present, that the pedigree ID is a UUID, and that width/height (when set) are positive integers.
- **HttpGateway** — narrow abstraction the tests fake.
- **EvageneClient** — knows the two endpoint shapes; depends on `HttpGateway`.
- **LabelMapper** — pure transform from pedigree detail plus label style to an ID → label mapping. Unknown generations fall back to `?-1`, `?-2`, ...
- **SvgDeidentifier** — pure transform from SVG text plus an old-name → new-label mapping to a rewritten SVG. Uses the language's XML parser (R `xml2`, Python `lxml`) so special characters in names can never escape the text node they belong to.
- **OutputWriter** — writes UTF-8 bytes to the requested path.
- **App** — composition root; wires the pieces.

## Test fixtures

- `fixtures/sample.svg` — a canonical SVG matching the shape that Evagene's `export.svg` endpoint emits.
- `fixtures/sample-detail.json` — the accompanying `PedigreeDetail` for label-mapping tests, with a deliberately awkward display name (`Linda <O'Brien> & Co`) to exercise XML escaping.
- `fixtures/deidentified.svg` — the expected output after a `generation-number` deidentification pass.

Tests assert *structural* parity — attribute sets, element counts, and text content — rather than string equality, so formatting changes in the XML serialiser do not cause spurious failures.

## Caveats

- This is an **academic / research example, not a validated de-identification tool**, not a medical device, and not fit for patient care. Any published figure that relies on real pedigrees remains the author's responsibility — including consent, ethics approval, and institutional review.
- Deidentification only rewrites the visible labels. It does *not* strip disease colour-coding, symbol shapes, or the structural shape of the pedigree itself, any of which can in principle re-identify a small enough family. Always review the output before publication.
- The `--width` and `--height` overrides update the root SVG attributes only; they leave the `viewBox` untouched so the figure scales cleanly at any resolution.
