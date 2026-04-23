# Pedigree OCR

**Photograph a hand-drawn pedigree, get a structured family history ready to review in one command -- and, one flag away, a real pedigree in [Evagene](https://evagene.net).**

The tool reads a photograph, scan, or PDF of a hand-drawn pedigree, asks Claude Vision (via your own Anthropic API key) to interpret the symbols -- squares, circles, filled shapes, slashes, double lines, MZ-twin chevrons -- and prints the result as pretty JSON plus a human-readable preview. With `--commit`, it uses the Evagene REST API to create the pedigree with proband, parents, grandparents, and siblings wired up -- the same sequence the `call-notes-to-pedigree` and `family-history-intake-form` demos use.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** -- it covers registering at [evagene.net](https://evagene.net), minting an API key, and configuring `EVAGENE_API_KEY` / `EVAGENE_BASE_URL`.

---

## Who this is for

- **Genetic counsellors** who sketch a pedigree on paper during a consultation and want a digital draft waiting in Evagene before the next session.
- **Teachers and clinical educators** converting textbook figures or training-set drawings into structured pedigrees.
- **Archivists** digitising pre-electronic case notes -- decades of pedigrees drawn on the back of a referral letter.
- **Integrators** wanting a short, auditable example of a BYOK multimodal-LLM pipeline that keeps the image out of Evagene's infrastructure.

## Which Evagene surfaces this uses

- **BYOK LLM (user side, vision)** -- the image is sent directly to Anthropic from this tool using the user's own `ANTHROPIC_API_KEY`. It never passes through Evagene.
- **REST API** -- when `--commit` is set: `POST /api/pedigrees`, `POST /api/individuals`, `POST /api/pedigrees/{id}/individuals/{ind_id}`, `PATCH /api/individuals/{id}` (proband), `POST /api/pedigrees/{id}/register/add-relative`.
- **Authentication** -- `X-API-Key: evg_...` with `write` scope (only needed for `--commit`).
- **Interactive API reference** -- [https://evagene.net/docs](https://evagene.net/docs).

### Privacy architecture

```
   image (.png/.jpg/.pdf)  ──►  this CLI  ──►  Anthropic (Claude Vision)
                                              (your ANTHROPIC_API_KEY)
                                    │
                                    │  extracted structured family
                                    ▼
                                  Evagene REST (only with --commit)
                                  (your EVAGENE_API_KEY)
```

Evagene never sees the image. Only the extracted, structured family data -- the same fields a clinician would type into the intake form -- reaches Evagene, and only when you explicitly pass `--commit`. The image and API keys are never logged; log lines that reference the image say `<image redacted, N KB>`.

## Prerequisites

1. An **Anthropic API key** -- [console.anthropic.com](https://console.anthropic.com). Export as `ANTHROPIC_API_KEY`. Confirm your organisation's Anthropic data-handling terms suit your clinical context before passing real drawings.
2. An **Evagene account and API key** with `write` scope for `--commit` -- see [../getting-started.md](../getting-started.md).
3. **Python 3.11+**.
4. **Poppler** (for `.pdf` input only): on Windows install from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add its `bin/` to `PATH`; on macOS `brew install poppler`; on Debian/Ubuntu `apt install poppler-utils`. PNG / JPG input needs no extra binaries.

## Configuration

Copy `python/.env.example` to `python/.env` and fill in the values.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | yes | — | Used for the vision call. Starts with `sk-ant-...`. |
| `EVAGENE_BASE_URL`  | no  | `https://evagene.net` | Override only if your organisation hosts Evagene elsewhere. |
| `EVAGENE_API_KEY`   | only with `--commit` | — | `write` scope. Starts with `evg_...`. |

The tool never logs either key or the image bytes.

## Command-line contract

```
pedigree-ocr <image.png|jpg|pdf> [--commit] [--show-prompt] [--model <model>]
```

- `<image-file>` -- positional path. `.png`, `.jpg`, `.jpeg`, or `.pdf` (first page).
- `--commit` -- after extraction, create the pedigree in Evagene (requires `EVAGENE_API_KEY`). Without it the tool is read-only.
- `--model <model>` -- override the default Claude vision model (`claude-opus-4-7`). Any vision-capable Claude model works.
- `--show-prompt` -- print the system prompt and JSON schema that would be sent to Anthropic, then exit. No network calls. Useful for auditing what the tool asks the model to do.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `64` | Usage / configuration error (missing image, bad extension, missing API key) |
| `69` | Evagene or Anthropic unreachable |
| `70` | Model output did not conform to the extraction schema |

## Run it

Only a Python implementation ships: the pipeline depends on `pdf2image` and the Anthropic vision SDK, and duplicating it in a second language would not add anything. `ANTHROPIC_API_KEY` is always required; `EVAGENE_API_KEY` is only required with `--commit`.

### Run it in Python 3.11+

**System prerequisite (only when input is a PDF):** install **Poppler** and put it on `PATH` — `pdf2image` shells out to it for the PDF→PNG step. `.png` / `.jpg` input does *not* need Poppler. Windows: grab a build from <https://github.com/oschwartz10612/poppler-windows/releases> and add its `bin/` to `PATH`. macOS: `brew install poppler`. Linux: `apt-get install poppler-utils` / `dnf install poppler-utils`.

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
python -m pedigree_ocr ../fixtures/sample-pedigree-drawing.png

# Run and commit to Evagene
python -m pedigree_ocr ../fixtures/sample-pedigree-drawing.png --commit

# Audit the prompt + schema without any network call
python -m pedigree_ocr --show-prompt
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

## Expected output

Without `--commit`, stdout is a pretty-printed JSON block matching the schema plus a readable preview. Example (from the synthetic fixture):

```
Extracted family
  proband  Emma (female)
  mother                 Grace -- Age 68 written under symbol.
  father                 Henry -- Age 70 written under symbol.
  maternal grandmother   Edith [affected] -- Filled circle, slash through symbol; deceased at 59.
  maternal grandfather   Cecil -- Age 92 written under symbol.
  paternal grandmother   Margaret -- Slash through symbol; deceased.
  paternal grandfather   Arthur [affected] -- Filled square; age 78 written under symbol.
  siblings
    - Alice (sister) [affected] -- Filled circle; age 42 written under symbol.
```

With `--commit`, two extra lines appear at the end:

```
Created pedigree 7c8d4d6a-...-...
https://evagene.net/pedigrees/7c8d4d6a-...-...
```

## Architecture

```
  image file (.png / .jpg / .pdf)
        │
        ▼
   ImageSource (pdf2image for PDF, verbatim for PNG/JPG)
        │
        ▼
   VisionExtractor ──►  LlmGateway (abstraction)
        │                concrete: Anthropic SDK with multimodal
        │                messages + tool_choice-forced JSON
        ▼
   ExtractedFamily (value object, one entry per relative,
                    with affection_status + free-text notes)
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

The `LlmGateway`, `PdfRenderer`, and `HttpGateway` abstractions let the tests exercise the full flow without touching the network, the disk, or a PDF renderer.

## Caveats

- **Always review before `--commit`.** OCR and symbol interpretation are imperfect. Run once read-only, eyeball the JSON and preview, fix the image or re-run before committing to Evagene. A vision model will sometimes miss a slash, read a filled circle as clear on a faint photocopy, or collapse MZ-twin chevrons into "two sisters".
- **Images may contain PHI.** With `ANTHROPIC_API_KEY` set, the drawing bytes are sent to Anthropic's API. Confirm your Anthropic data-handling terms (zero-retention, ZDR add-on, enterprise agreement, etc.) suit your clinical context before passing real patient material. Redact names and identifiers on the drawing beforehand if in doubt.
- **Symbols the schema does not express -- twins, consanguinity, multiple marriages, step-relatives -- land in free-text `notes`, not structured fields.** That is intentional: a reviewer should translate a drawing's shading or chevron into a coded Evagene relationship, not a vision model. Review the notes and fix up in the Evagene UI.
- **Diseases are captured as free-text `notes`, not coded.** The schema keeps proband / parents / grandparents / siblings structured; any affection information mentioned on the drawing is preserved in a per-relative `notes` field so a clinician can read it, but not translated into Evagene's structured disease codes.
- This is an example integration, not a validated clinical tool. Clinical governance applies.
