# Call notes to pedigree

**Paste a transcript, get a structured family history ready to review in ten seconds — and, one flag away, a real pedigree in [Evagene](https://evagene.net).**

The tool reads a free-text transcript from stdin or a file, asks Claude (via your own Anthropic API key) to extract proband, parents, grandparents, and siblings, and prints the result as pretty JSON plus a human-readable preview. With `--commit`, it then uses the Evagene REST API to create the pedigree and wire the relatives up — the same sequence the `family-history-intake-form` demo uses.

This is an academic / research example of a BYOK LLM pipeline that keeps the transcript out of Evagene's infrastructure. It is a reference implementation for study and experimentation, not a clinical extraction tool.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and configuring `EVAGENE_API_KEY` / `EVAGENE_BASE_URL`.

---

## Who this is for

- **Developers and integrators** wanting a short, auditable example of a BYOK LLM pipeline where the transcript is sent directly to the user's chosen LLM provider and never passes through Evagene.
- **Researchers** studying how well a structured extraction schema holds up against synthetic counselling transcripts — the `--show-prompt` flag exposes the exact system prompt for audit.
- **Educators and students** exploring tool-use / structured-output prompting and the mechanics of a two-stage (extract → commit) pipeline with an explicit review step.

## Which Evagene surfaces this uses

- **BYOK LLM (user side)** — the transcript is sent directly to Anthropic from this tool using the user's own `ANTHROPIC_API_KEY`. It never passes through Evagene.
- **REST API** — when `--commit` is set: `POST /api/pedigrees`, `POST /api/individuals`, `POST /api/pedigrees/{id}/individuals/{ind_id}`, `PATCH /api/individuals/{id}` (proband), `POST /api/pedigrees/{id}/register/add-relative`.
- **Authentication** — `X-API-Key: evg_...` with `write` scope (only needed for `--commit`).
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs).

### Privacy architecture

```
   transcript  ──►  this CLI  ──►  Anthropic (Claude)
                                  (your ANTHROPIC_API_KEY)
                        │
                        │  extracted structured family
                        ▼
                      Evagene REST (only with --commit)
                      (your EVAGENE_API_KEY)
```

Evagene never sees the raw transcript. Only the extracted, structured family data — the same fields the intake form demo captures — reaches Evagene, and only when you explicitly pass `--commit`.

## Prerequisites

1. An **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com). Export it as `ANTHROPIC_API_KEY`. Review Anthropic's data-handling terms before passing anything sensitive through the pipeline — and prefer synthetic transcripts for experimentation.
2. An **Evagene account and API key** with `write` scope for `--commit` — see [../getting-started.md](../getting-started.md).
3. A recent runtime for the language you prefer.

## Configuration

Each language folder ships a `.env.example`. Copy to `.env` and fill in.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | yes | — | Used for the extraction call. Starts with `sk-ant-...`. |
| `EVAGENE_BASE_URL`  | no  | `https://evagene.net` | Override only if your organisation hosts Evagene elsewhere. |
| `EVAGENE_API_KEY`   | only with `--commit` | — | `write` scope. Starts with `evg_...`. |

The tool never logs either key.

## Command-line contract

```
call-notes-to-pedigree [<transcript-file>] [--commit] [--model <model>] [--show-prompt]
```

- `<transcript-file>` — positional path. If omitted, the transcript is read from stdin.
- `--commit` — after extraction, create the pedigree in Evagene (requires `EVAGENE_API_KEY`). Without it the tool is read-only.
- `--model <model>` — override the default Claude model (`claude-sonnet-4-6`).
- `--show-prompt` — print the system prompt and JSON schema that would be sent to Anthropic, then exit. No network calls. Useful for auditing what the tool asks the model to do.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `64` | Usage / configuration error |
| `69` | Evagene or Anthropic unreachable |
| `70` | Model output did not conform to the extraction schema |

## Run it

Both implementations always need `ANTHROPIC_API_KEY`; `EVAGENE_API_KEY` is only needed for `--commit`. Piping a transcript on stdin also works (e.g. `cat transcript.txt | python -m call_notes_to_pedigree`).

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

# Set your API keys (one shell session)
# Windows PowerShell:
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export ANTHROPIC_API_KEY=sk-ant-...
export EVAGENE_API_KEY=evg_...

# Run read-only
python -m call_notes_to_pedigree ../fixtures/sample-transcript.txt

# Run and commit to Evagene
python -m call_notes_to_pedigree ../fixtures/sample-transcript.txt --commit
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

# Set your API keys (one shell session)
# Windows PowerShell:
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export ANTHROPIC_API_KEY=sk-ant-...
export EVAGENE_API_KEY=evg_...

# Run read-only
npm start -- ../fixtures/sample-transcript.txt

# Run and commit to Evagene
npm start -- ../fixtures/sample-transcript.txt --commit
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

## Expected output

Without `--commit`, stdout is a pretty-printed JSON block matching the schema plus a readable preview:

```json
{
  "proband": { "display_name": "Emma Carter", "biological_sex": "female", "year_of_birth": 1985, "notes": null },
  "mother":  { "display_name": "Grace", "year_of_birth": 1957, "notes": null },
  ...
}
```

```
Extracted family
  proband  Emma Carter (female, b.1985)
  mother   Grace (b.1957)
  father   Henry (b.1955)
  ...
  siblings
    - Alice (sister, b.1983) — Breast cancer diagnosed at 41.
    - Ben (half_brother) — Paternal half-brother, around 50, healthy.
```

With `--commit`, two extra lines appear at the end:

```
Created pedigree 7c8d4d6a-...-...
https://evagene.net/pedigrees/7c8d4d6a-...-...
```

## Architecture (same split in both languages)

```
  transcript (stdin / file)
        │
        ▼
   TranscriptSource          ─ reads text, no parsing
        │
        ▼
   AnthropicExtractor ──►  LlmGateway (abstraction)
        │                   concrete: Anthropic SDK with tool-use schema
        ▼
   ExtractedFamily (value object)
        │
        ├─►  Presenter         (always)
        │       pretty JSON + human-readable preview
        │
        └─►  EvageneWriter     (only with --commit)
                   │
                   ├─► EvageneClient.createPedigree
                   ├─► EvageneClient.createIndividual      (proband)
                   ├─► EvageneClient.addIndividualToPedigree
                   ├─► EvageneClient.designateAsProband
                   └─► EvageneClient.addRelative           (per relative, in order)
                                     │
                                     ▼
                              HttpGateway (abstraction)
```

Every module has one responsibility. The `LlmGateway` and `HttpGateway` abstractions mean the tests can run the whole flow end-to-end without touching either network.

## Caveats

- This is an **academic / research example, not a validated clinical tool**, not a medical device, and not fit for patient care. Experiment with synthetic transcripts; do not feed real patient material through the pipeline.
- **Always review before `--commit`.** LLM extraction is imperfect. Run once read-only, eyeball the JSON and preview, fix the transcript or re-run before anything is written.
- **Transcripts travel to a third-party LLM.** With `ANTHROPIC_API_KEY` set, the raw transcript is sent to Anthropic's API. Whatever you feed in leaves your environment — another reason to stick to synthetic data for experimentation and to review Anthropic's data-handling terms before going further.
- **Diseases and conditions are captured as free-text `notes`, not coded.** The schema keeps proband / parents / grandparents / siblings structured; disease diagnoses mentioned in the transcript are preserved in a per-relative `notes` field so a reader can see them, but they are not translated into Evagene's structured disease codes. Structured disease coding is future work, and getting it wrong silently is worse than leaving it to the reader.
