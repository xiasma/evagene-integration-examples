# Cascade screening letters

**Draft a personalised letter for every first- and second-degree relative in a pedigree, in one command.** Point this at an [Evagene](https://evagene.net) pedigree and the tool asks the Evagene register who the first- and second-degree relatives are, runs an analysis template against the pedigree to generate a family-specific letter body, and writes one Markdown file per relative into a folder for review.

This is an academic / research example of combining the Evagene family register with the analysis-templates endpoint. It is a reference implementation, not a clinical letter-generation tool.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Developers and integrators** wanting a worked example of combining the Evagene family register with the analysis-templates endpoint.
- **Researchers and educators** experimenting with variable-injection patterns in LLM-generated document output, using synthetic pedigrees.
- **Students** studying how to compose a register query, a template-run call, and a per-relative document write into one cohesive pipeline.

## What it does, step by step

1. Calls `GET /api/pedigrees/{id}/register` to list everyone in the pedigree with their relationship label to the proband.
2. Filters that list to first-degree relatives (parent / child / sibling) and second-degree relatives (grandparent / aunt / uncle / niece / nephew / half-sibling).
3. Finds or creates a conservative analysis template named `cascade-screening-letter` via `GET /api/templates` and `POST /api/templates`.
4. Runs the template once against the pedigree via `POST /api/templates/{id}/run?pedigree_id=...` to produce a family-specific letter body (proband name, disease list, risk summary injected).
5. Composes one letter per at-risk relative locally — a personalised salutation and relationship sentence followed by the template body — and writes it to a Markdown file.

In a real workflow (which this demo is not), a reader would review each file, add appropriate letterhead and contact details, and decide what to do with it. As an academic example, leave the output in place and treat it as study material.

## What Evagene surfaces this uses

- **REST API — family register** — `GET /api/pedigrees/{pedigree_id}/register`.
- **REST API — analysis templates** — `GET /api/templates`, `POST /api/templates`, `POST /api/templates/{template_id}/run?pedigree_id=...`.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scope `analyze` is sufficient (covers both reads and template execution).
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account and an API key with `analyze` scope — see [getting-started.md](../getting-started.md).
2. A pedigree with a designated **proband**, at least one **at-risk relative** in the first- or second-degree circle, and a disease recorded on the family (the tool reads the register and the template's disease-list variable).
3. A recent runtime for the language you prefer — only one is needed.

## Configuration

Every language reads the same environment variables. Each language folder ships a `.env.example` you can copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

## Command-line contract

Both implementations accept the same invocation:

```
cascade-letters <pedigree-id> [--output-dir <dir>] [--template <id>] [--dry-run]
```

- `pedigree-id` — UUID of the pedigree.
- `--output-dir` — directory to write letters into; defaults to `./letters` (created if missing).
- `--template` — UUID of the analysis template to use; defaults to auto-discover or create one named `cascade-screening-letter`.
- `--dry-run` — print the list of relatives a letter would be generated for, then stop. No template execution, no files written.

Stdout: one line per generated file — the file's path — so the output pipes cleanly into `xargs` or a review tool.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — letters written (or dry-run completed). |
| `64` | Usage error (missing or malformed arguments). |
| `69` | Evagene API unreachable or returned a non-2xx response. |
| `70` | Register has no at-risk relatives, or no proband is designated. |

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

# Install the demo package + its dev tools (editable install so python -m <pkg> works)
pip install -e ".[dev]"

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
python -m cascade_letters <pedigree-id>
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

## Expected output

Dry run against a BRCA family pedigree:

```
$ python -m cascade_letters a1cfe665-2e95-4386-9eb8-53d46095478a --dry-run
Margaret Ward (Mother)
David Ward (Father)
Sarah Ward (Sister)
Thomas Ward (Brother)
Joan Pembroke (Aunt (maternal))
Elizabeth Pembroke (Grandmother (maternal))
```

Full run, writing Markdown files:

```
$ python -m cascade_letters a1cfe665-2e95-4386-9eb8-53d46095478a
letters/01-margaret-ward.md
letters/02-david-ward.md
letters/03-sarah-ward.md
letters/04-thomas-ward.md
letters/05-joan-pembroke.md
letters/06-elizabeth-pembroke.md
```

A generated letter looks like the one at `fixtures/sample-template-run.md` — see that file for the full format.

## Architecture

Both languages follow the same shape; each module has a single responsibility.

```
 CLI args + env  ─┐
                  ├─► Config (value object, validated)
 EVAGENE_API_KEY ─┘             │
                                ▼
                         EvageneClient ◄── HttpGateway (abstraction)
                                │
                ┌───────────────┼────────────────────┐
                ▼               ▼                    ▼
        fetch_register   template_resolver      run_template
                │               │                    │
                ▼               ▼                    ▼
       RelativeSelector  (find or create)     LetterWriter  (sink)
                │
                └────────────► CascadeService (orchestrator)
```

- **Config** — immutable value object; validates `EVAGENE_API_KEY` is present and that IDs are UUIDs.
- **HttpGateway** — narrow abstraction the tests fake.
- **EvageneClient** — one method per endpoint (`fetch_register`, `list_templates`, `create_template`, `run_template`).
- **RelativeSelector** — pure filter: `RegisterData` in, list of letter targets out (first- and second-degree only, skips the proband, skips rows without a display name).
- **TemplateResolver** — either returns the user-provided template ID, or looks one up by name, or creates a fresh one with a conservative default body.
- **LetterWriter** — composes the final Markdown locally (personalised salutation + template body) and writes it to an injected sink. `DiskLetterSink` writes files; tests use an in-memory sink.
- **CascadeService** — orchestrator; selector + resolver + one `run_template` call + writer.
- **App** — composition root.

## Test fixtures

- `fixtures/sample-register.json` — a realistic BRCA family register response.
- `fixtures/sample-template-run.md` — an example of what a generated letter looks like after local composition.

## Caveats

- This is an **academic / research example, not a validated clinical workflow**, not a medical device, and not fit for patient care. Do not use it to send real letters to real relatives.
- **Generated letters are example drafts.** They are illustrative output — review every line, and treat them as study material, not correspondence.
- **Personal information, if you use real data, ends up in the output folder.** The demo does not encrypt anything. Prefer synthetic pedigrees for experimentation; if real data is ever used, apply the same data-handling controls you would to any other sensitive document.
- **The auto-created default template is a conservative starting point** ("you may wish to consider speaking with your genetic counsellor about..."). Review and replace it to match whatever style is appropriate for the context you are experimenting in.
