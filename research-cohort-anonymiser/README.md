# Research cohort anonymiser

**Paste a pedigree ID and get a research-safe copy of the family in one command.** Names are replaced with generation-indexed identifiers (`I-1`, `II-3`, `III-1`, ...); dates of birth are rounded to a bucket you choose; free-text notes and comments are stripped; structure (relationships, eggs, twin modelling, consanguinity coefficients, disease IDs, affection status) is preserved exactly. Write the output to stdout, to a file, or as a brand-new pedigree on the same [Evagene](https://evagene.net) account.

Useful when you are about to share a pedigree outside the clinic and would rather not rely on remembering to scrub every direct identifier by hand.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Important — read before using

This tool performs **structural de-identification**, not HIPAA Safe-Harbor de-identification. In particular it does not:

- remove identifiers hidden inside free-text *values* (only free-text *keys* named `note` / `comment` / `description` are stripped);
- coarsen geographic information or rare disease combinations that might re-identify a family;
- audit pedigrees for Expert Determination under 45 CFR 164.514(b)(1);
- tell you whether the cohort you are sharing meets your institution's IRB or ethics-board requirements.

Treat it as **scaffolding**: a first pass that removes the obvious identifiers and exposes a k-anonymity estimate you can reason about, not a replacement for a proper privacy review. For a formal release, route the output through your institution's de-identification workflow.

The k-anonymity estimate prints alongside the pedigree and is deliberately coarse — bucketed only on sex, decade of birth, and affected-disease count. It is a tripwire, not a proof. A pedigree with k = 1 (one individual sits in a bucket of their own) is not automatically identifiable, and k >= 5 is not automatically safe. Use the number to notice surprises; use judgement to decide what to release.

---

## Who this is for

- **Researchers** preparing pedigrees for a paper, supplement, or data repository.
- **Research genetic counsellors** sharing an interesting family with a collaborator.
- **Data stewards** building bulk de-identification pipelines for an archive.
- **Developers** who want a small, readable example of round-tripping Evagene `PedigreeDetail` JSON.

## What Evagene surfaces this uses

- **REST API** — `GET /api/pedigrees/{id}` to fetch the source.
- **REST API** (when `--as-new-pedigree`) — `POST /api/pedigrees`, `POST /api/individuals`, `POST /api/pedigrees/{id}/individuals/{id}`, `PATCH /api/individuals/{id}`, and `POST /api/pedigrees/{id}/register/add-relative`. This is the same sequence the `family-history-intake-form` demo uses.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scope `read` is enough for stdout/file output; `write` is required for `--as-new-pedigree`.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs).

## Prerequisites

1. An Evagene account and an API key — see [getting-started.md](../getting-started.md).
2. A pedigree to anonymise. Families with a designated proband are required if you plan to use `--as-new-pedigree`.
3. A recent runtime for the language you prefer (Python 3.11+ or R 4.3+).

## Configuration

Every language reads the same environment variables.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | —                     | `evg_...` |

## Command-line contract

```
anonymise <pedigree-id> [--output <file.json>] [--as-new-pedigree]
                        [--age-precision year|five-year|decade]
                        [--keep-sex | --no-keep-sex]
```

| Flag | Default | Effect |
|---|---|---|
| *none* | — | Print anonymised JSON to stdout. |
| `--output <path>` | — | Write anonymised JSON to a file instead. |
| `--as-new-pedigree` | off | Create a fresh pedigree on your account with the anonymised content; print its ID. Mutually exclusive with `--output`. |
| `--age-precision year` | year | First-of-year DOBs (e.g. `1968-01-01`). |
| `--age-precision five-year` | — | Nearest multiple of five (`1965-01-01`). |
| `--age-precision decade` | — | Nearest decade (`1960-01-01`). |
| `--keep-sex` | on | Preserve `biological_sex`. Kept by default because sex drives structural pedigree inference. |
| `--no-keep-sex` | — | Redact to `unknown`. |

### Exit codes

| Code | Meaning |
|---|---|
| `0`  | Anonymised output emitted successfully. |
| `64` | Usage error (missing arguments, not a UUID, conflicting flags). |
| `69` | Evagene API call failed (unreachable, non-2xx, missing proband for `--as-new-pedigree`). |
| `70` | Response did not match the documented `PedigreeDetail` shape. |

## Anonymisation rules

Every rule lives in a tested helper; the orchestrator is a straight-line composition of them.

- **Names** — `display_name` and the structured `name` block are replaced with a stable, generation-indexed identifier (`I-1`, `I-2`, `II-1`, ...). Ordering within a generation is stable on source UUID so the labels do not drift between runs.
- **Dates** — every ISO-8601 date (`date_represented`, `date_start`, `date_end`) is truncated to the start of the chosen bucket (year / five-year / decade).
- **Free text** — properties whose key contains `note`, `comment`, or `description` (case-insensitive) are stripped. Properties whose *values* are free text are **not** stripped; the README note above explains why.
- **Ages** — numeric `age_at_event` properties are rounded to the same bucket as dates.
- **Structure** — relationships, eggs, consanguinity coefficients, twin modelling via shared eggs, disease IDs, affection status, and manifestations are preserved exactly. The whole point of a research pedigree is the pattern — we keep it.
- **Sex** — biological sex is preserved by default (it is load-bearing for Mendelian inference). Pass `--no-keep-sex` to redact.

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

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
python -m research_anonymiser <pedigree-id>
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
Rscript -e 'loc <- Sys.getenv("R_LIBS_USER"); if (!dir.exists(loc)) dir.create(loc, recursive = TRUE, showWarnings = FALSE); .libPaths(c(loc, .libPaths())); install.packages(c("httr2", "jsonlite", "testthat"), repos = "https://cloud.r-project.org")'

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
Rscript inst/bin/anonymise.R <pedigree-id>
```

Run the tests (optional):

```bash
Rscript -e 'loc <- Sys.getenv("R_LIBS_USER"); .libPaths(c(loc, .libPaths())); testthat::test_dir("tests/testthat")'
```

## Expected output

```json
{
  "display_name": "Anonymised pedigree",
  "date_represented": "2026-01-01",
  "individuals": [
    {
      "id": "...",
      "display_name": "III-1",
      "generation_label": "III",
      "biological_sex": "female",
      "proband": 270,
      ...
    }
  ],
  "k_anonymity": {
    "k": 1,
    "bucket_count": 7,
    "smallest_bucket_key": ["female", "1942", 1],
    "total_individuals": 7
  }
}
```

With `--as-new-pedigree`, the tool emits the new pedigree's UUID to stdout instead — suitable for piping into a subsequent API call.

## Architecture (identical in both languages)

```
  CLI args + env
        |
        v
     Config -----------------------------------+
        |                                       |
        v                                       |
  EvageneClient.get_pedigree_detail   <--- HttpGateway (abstraction)
        |
        v
  assign_generation_labels  (pure)
        |
        v
  anonymise_pedigree + AnonymisationRules  (pure)
        |
        v
  estimate_k_anonymity  (pure)
        |
        v
  render_json  (deterministic)
        |
        v
  OutputSink:  stdout | file | EvageneClient.rebuild_pedigree
```

- **Config** — immutable value object; validates the API key, UUID, and mutually-exclusive flags.
- **HttpGateway** — narrow abstraction the tests fake; production uses `httx` (Python) or `httr2` (R).
- **EvageneClient** — one method per endpoint plus a `rebuild_pedigree` orchestrator that mirrors the intake-form demo's sequence.
- **generation_assigner** — pure; derives generations from eggs + relationships, aligning spouses to each other's generation.
- **anonymiser** — pure; each rule is a small named helper tested in isolation.
- **k_anonymity_estimator** — pure; quasi-identifier bucketing.
- **presenter** — deterministic key ordering so diffs are clean.
- **writer** — three interchangeable sinks: stdout, file, or a new pedigree on the account.
- **App** — composition root; wires the pieces and maps errors to exit codes.

## Test fixtures

- `fixtures/source-pedigree.json` — a realistic three-generation BRCA family with names, DOBs, and a scatter of free-text notes to exercise the stripping rules.
- `fixtures/expected-anonymised.json` — golden output at `--age-precision=year --keep-sex`.
- `fixtures/expected-anonymised-decade.json` — golden output at `--age-precision=decade --keep-sex`.

If the Evagene response shape changes, update the source fixture and regenerate the two goldens.

## Caveats

- **Structural de-identification only.** See the banner at the top of this README.
- **k-anonymity is a signal, not a proof.** Small pedigrees will almost always produce k = 1. Use the estimate to notice re-identification risk, not to certify safety.
- **Free-text values are not scrubbed.** The rule only looks at property *keys*. If you maintain a clinic-reference scheme whose values encode patient initials, you will need a bespoke pass.
- **The `--as-new-pedigree` rebuild is best-effort for complex topologies.** It walks the egg graph breadth-first from the proband and issues one `add-relative` call per non-proband individual. Pedigrees with sibling-in-law partnerships, multiple marriages, or other structures outside the `add-relative` enum may need manual tidying afterwards.
- This is an example integration, not a validated clinical tool.
