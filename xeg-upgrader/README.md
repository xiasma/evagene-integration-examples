# xeg-upgrader

**Migrate legacy Evagene v1 `.xeg` XML pedigrees into the current data model.** Point this at an archived `.xeg` file and it validates the file against [Evagene](https://evagene.net), prints a summary of the individuals, relationships, eggs, events, and diseases recovered from it, and — when you are happy with the preview — creates a real pedigree from it in one command.

Built for clinics migrating off an older on-premise Evagene deployment, genetic nurses with a folder of archived files that predate the JSON/register model, and developers writing one-off scripts that consume `.xeg` files.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## Who this is for

- **Clinics migrating archives** — take a folder of `.xeg` files off an older deployment, preview each one to catch silently-dropped data, then commit the clean ones.
- **Genetic counsellors / nurses** who still receive the occasional `.xeg` file from a collaborating site — a single command verifies the file is intact before the family is opened in the canvas.
- **Integrators / developers** wanting a small, complete example of talking to Evagene's file-import surface cleanly from .NET or Python.

## What Evagene surfaces this uses

- **REST API** — `POST /api/pedigrees/{id}/import/xeg?mode=parse` (preview), `POST /api/pedigrees/{id}/import/xeg` (commit), `POST /api/pedigrees`, `DELETE /api/pedigrees/{id}`.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scope `write` is required because the import endpoint mutates the pedigree.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) or [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account and an API key with `write` scope — see [getting-started.md](../getting-started.md).
2. A legacy Evagene v1 `.xeg` XML file to migrate. The `fixtures/` folder ships a three-generation synthetic family you can practise on.
3. A recent runtime for the language you prefer (.NET 8+ or Python 3.11+).

## Configuration

Each language folder ships a `.env.example` you can copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

## Command-line contract

Both implementations accept the same invocation:

```
xeg-upgrade <input.xeg> [--create] [--name <display-name>] [--preview]
```

- `input.xeg` — path to the legacy `.xeg` file.
- `--preview` (default) — parse only; the tool creates a scratch pedigree, asks Evagene to parse the file against it in `?mode=parse` (which does not mutate), deletes the scratch pedigree, and prints the summary. Nothing persists.
- `--create` — create a pedigree and import the file into it for real. Prints the new pedigree's ID and URL alongside the summary.
- `--name` — override the display name used when `--create` builds the pedigree. Defaults to the file stem (e.g. `hill-family.xeg` becomes `hill-family`).

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — preview rendered or pedigree created |
| `64` | Usage error (missing or malformed arguments) |
| `69` | Evagene API unreachable or returned a non-2xx response |
| `70` | Input file is not a well-formed v1 `.xeg` |

## Run it

Both implementations expect `EVAGENE_API_KEY` in the environment. Preview is the default; `--create` persists the pedigree.

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

# Preview
python -m xeg_upgrader ../fixtures/sample-simple.xeg

# Create a real pedigree
python -m xeg_upgrader ../fixtures/sample-simple.xeg --create --name "Hill family"
```

Run the tests (optional):

```bash
pytest
ruff check
mypy --strict src
```

### Run it in .NET 8+

```bash
cd dotnet

# Restore NuGet packages
dotnet restore

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Preview
dotnet run --project src/XegUpgrader -- ../fixtures/sample-simple.xeg

# Create a real pedigree
dotnet run --project src/XegUpgrader -- ../fixtures/sample-simple.xeg --create --name "Hill family"
```

Run the tests (optional):

```bash
dotnet test
```

## Expected output

```
File: sample-simple.xeg
Mode: preview (no pedigree created)

Counts
  individuals    5
  relationships  2
  eggs           2
  diseases       1
  events         6

Diseases
  - Breast Cancer

Warnings
  (none)
```

Under `--create` the same block is followed by the new pedigree's ID and URL.

## Architecture (identical in both languages)

```
 CLI args + env  ─┐
                  ├─►  Config (value object, validated)
 EVAGENE_API_KEY ─┘              │
                                 ▼
     .xeg file   ─►   XegReader (pure: XDocument/lxml, root check)
                                 │
                                 ▼
                         EvageneClient  ◄── HttpGateway (abstraction)
                                 │
                            parse / commit
                                 ▼
                         SummaryPrinter (pure)
                                 │
                                 ▼
                           stdout / stderr
```

- **Config** — immutable value object; parses CLI args and validates the environment.
- **XegReader** — loads the file and confirms it is well-formed XML rooted at `<Pedigree>` before a byte goes over the wire. Uses `System.Xml.Linq` in .NET and `lxml` in Python.
- **HttpGateway** — narrow abstraction the tests fake.
- **EvageneClient** — four small methods: `create_pedigree`, `import_xeg_parse_only`, `import_xeg`, `delete_pedigree`. Each maps to one endpoint.
- **SummaryPrinter** — pure transform from parse-mode JSON to a `ParseSummary` and then to text. Flags individuals with unknown biological sex, orphaned eggs, and manifestations pointing at unknown diseases.
- **App** — composition root; wires the pieces and drives either preview or create.

## Test fixtures

- `fixtures/sample-simple.xeg` — three-generation family, one breast-cancer case, well-formed.
- `fixtures/sample-with-warnings.xeg` — same but with a couple of minor inconsistencies that exercise the warning paths.
- `fixtures/malformed.xeg` — intentionally broken; used for negative tests.
- `fixtures/sample-simple-parsed.json` — a synthetic parse response matching `sample-simple.xeg`, used by the summary-printer snapshot test.
- `fixtures/expected-summary.txt` — the canonical rendered summary for the snapshot test.

## Caveats

- This is an example integration, not a validated migration tool. For a large archive, preview every file first and spot-check commit results in the Evagene web app.
- The legacy `.xeg` schema carried fields the current data model does not (layout coordinates, certain event sub-types). Evagene's parser translates what it can and drops or maps the rest — the parse summary reports what survived the translation.
- Preview mode still needs to create (and delete) a scratch pedigree because `POST /api/pedigrees/{id}/import/xeg?mode=parse` is scoped to an owned pedigree even when it does not mutate it. The scratch pedigree is soft-deleted on exit.
