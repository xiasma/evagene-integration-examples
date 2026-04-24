# Pedigree puzzle generator

**Generate a fresh "what is the mode of inheritance?" pedigree puzzle in one command — a drawn pedigree hosted on [Evagene](https://evagene.net), a question card, and an answer key, ready for a classroom.**

Pick a Mendelian mode (AD, AR, XLR, XLD, MT) or leave the default (`random`) and the tool builds a synthetic three- or four-generation family, draws it as a pedigree on your Evagene account, downloads the SVG, and writes a matching **question.md** and **answer.md** pair into a timestamped folder. The scratch pedigree is deleted when the run finishes so your account stays tidy; the files stay.

This is an educational / academic example: it is pure teaching material, with no clinical relevance and no real pedigree data involved.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and configuring `EVAGENE_API_KEY` / `EVAGENE_BASE_URL`.

---

## Who this is for

- **Lecturers and teaching staff** who want an endless supply of unique puzzles without drawing them by hand.
- **Textbook authors and e-learning producers** needing attributable, clean SVGs of example pedigrees.
- **Students preparing for exams** — run the tool with `--mode random`, solve the puzzle, then open `answer.md` to check.

## What Evagene surfaces this uses

- **REST API** — `POST /api/pedigrees`, `POST /api/individuals`, `POST /api/pedigrees/{id}/individuals/{ind_id}`, `PATCH /api/individuals/{id}` (for the proband flag), `POST /api/pedigrees/{id}/register/add-relative`, `POST /api/individuals/{id}/diseases`, `GET /api/diseases`, `GET /api/pedigrees/{id}/export.svg`, and `DELETE /api/pedigrees/{id}`.
- **Authentication** — long-lived API key via `X-API-Key: evg_...` with `write` scope (the run creates and deletes pedigree data on your account).
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs).

## Prerequisites

1. An Evagene account and an API key with `write` scope — see [../getting-started.md](../getting-started.md).
2. A recent runtime for the language you prefer.

## Configuration

Each language folder ships a `.env.example`. Copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

## Command-line contract

```
puzzle-generator [--mode AD|AR|XLR|XLD|MT|random]
                 [--generations 3|4]
                 [--size small|medium|large]
                 [--disease <name-or-id>]
                 [--output-dir <dir>]
                 [--no-cleanup]
                 [--seed <int>]
```

| Flag | Default | Notes |
|---|---|---|
| `--mode` | `random` | Inheritance pattern to illustrate. `random` picks one per run. |
| `--generations` | `3` | Number of generations in the family. `3` or `4`. |
| `--size` | `medium` | Children per couple: `small` = 2–3, `medium` = 3–5, `large` = 5–7. |
| `--disease` | curated per mode | Disease display name resolved via `GET /api/diseases`. Defaults: Huntington's (AD), Cystic Fibrosis (AR), Haemophilia A (XLR), Rett Syndrome (XLD), Leber Hereditary Optic Neuropathy (MT). |
| `--output-dir` | `./puzzles` | Directory the timestamped puzzle folder is written into. |
| `--no-cleanup` | off | Keep the scratch pedigree on your Evagene account (default is to delete). |
| `--seed` | random | Integer seed for the pedigree generator — same seed + same flags ⇒ same puzzle. |

**Exit codes:** `0` success · `64` usage error · `69` Evagene API unavailable · `70` internal error.

## Run it

Both implementations expect `EVAGENE_API_KEY` in the environment (the tool mints and deletes pedigrees in your account).

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
python -m pedigree_puzzle --mode AR
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
npm start -- --mode AR
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

## Expected output

```
Wrote puzzles/puzzle-20260420-143012/question.md
Wrote puzzles/puzzle-20260420-143012/answer.md
Pedigree on Evagene: https://evagene.net/pedigrees/7c8d4d6a-... (deleted)
```

The folder contains three files:

- `pedigree.svg` — the rendered family pedigree downloaded from Evagene.
- `question.md` — embeds the SVG, names the proband, and asks the student to pick the mode.
- `answer.md` — names the mode, lists the cues that point at it, and includes the textbook-style teaching note.

If `--no-cleanup` is passed, the scratch pedigree stays on your account at `<EVAGENE_BASE_URL>/pedigrees/<id>` so students can explore it interactively; otherwise it is deleted when the run finishes.

## Architecture (identical in every language)

```
          CLI args + env
                │
                ▼
             config  (pure parse)
                │
                ▼
        puzzle_blueprint  (pure, seeded)
                │
                ▼
          orchestrator  ──► evagene_client ──► http_gateway
                │                (REST)          (httpx/fetch)
                ├──► answer_explainer (pure)
                └──► writer  (filesystem)
```

- **config** — parses CLI + env into an immutable `Config`.
- **puzzle_blueprint** — pure: given `(mode, generations, size, seed)` it returns a deterministic `PedigreeBlueprint` (individuals with relationships + affected flags). Tests lock expected blueprints on specific seeds.
- **mode_heuristics** — pure: offspring-affected probabilities and teaching cues per mode.
- **answer_explainer** — pure: blueprint + disease name → educational Markdown.
- **evagene_client** — thin REST wrapper, one method per endpoint.
- **http_gateway** — abstraction over `httpx` / `fetch`, replaced by a fake in tests.
- **writer** — writes `question.md`, `answer.md`, and `pedigree.svg` into a timestamped folder.
- **orchestrator** — composes the blueprint into live API calls, downloads the SVG, invokes the writer, deletes the scratch pedigree.
- **app** — composition root; wires concretes to abstractions and runs the CLI.

## Caveats

- This is an **academic / educational example**. The generated pedigrees are synthetic teaching artefacts and carry no clinical meaning. Do not present the output as real case material.
- This generator uses **idealised Mendelian rules** (full penetrance, no de novo, no anticipation) — realistic pedigrees in research or clinical datasets will look messier.
- The disease catalogue is fixed by the Evagene service. If you ask for a disease name it cannot find, the run fails fast with a `DiseaseNotFoundError`.
- "Mode of inheritance" is the teaching answer; real-world risk analysis takes many more features into account and belongs with qualified professionals.
