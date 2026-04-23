# Family-history intake form

**Capture three generations of family history in under two minutes, end up with a fully-structured pedigree in [Evagene](https://evagene.net).**

Paste a handful of names and birth years into a one-page web form; the server calls the Evagene REST API to create the pedigree, designates the patient as the proband, and wires up parents, grandparents, and any siblings via the `/register/add-relative` endpoint. On success the browser lands on the Evagene web app at the new pedigree — ready for the clinician to add diagnoses, import a GEDCOM, or run a risk calculation.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and configuring `EVAGENE_API_KEY` / `EVAGENE_BASE_URL`.

---

## Who this is for

- **GPs and primary-care doctors** running a family-history triage at the point of referral — intake takes 90 seconds instead of hand-drawing a pedigree on the back of a referral letter.
- **Genetic nurses** who need a quick, structured way to capture a new family's skeleton before they sit down with the proband.
- **Practice IT / integrators** wanting a small, auditable example of how to orchestrate `create pedigree → create proband → add-relative` against the Evagene API.

## What Evagene surfaces this uses

- **REST API** — `POST /api/pedigrees`, `POST /api/individuals`, `POST /api/pedigrees/{id}/individuals/{ind_id}`, `PATCH /api/individuals/{id}` (to designate the proband), `POST /api/pedigrees/{id}/register/add-relative`.
- **Authentication** — long-lived API key via `X-API-Key: evg_...` with `write` scope.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs).

## What the form captures

| Section | Fields |
|---|---|
| **Patient (proband)** | Name *(required)*, biological sex, year of birth |
| **Parents** | Mother (name, year), Father (name, year) |
| **Maternal grandparents** | Maternal grandmother + grandfather (name, year each) |
| **Paternal grandparents** | Paternal grandmother + grandfather (name, year each) |
| **Siblings** | Up to 4 rows: name, relationship (sister / brother / half-sister / half-brother), year |

Every field except the patient's name is optional. Blank rows are skipped — the resulting pedigree contains only the relatives you typed.

Diagnoses, DNA results, consanguinity, and the rest of Evagene's clinical detail live in the web app. The intake form is deliberately structural — it builds the skeleton, then hands you off to Evagene to put flesh on it.

## Prerequisites

1. An Evagene account and an API key with `write` scope — see [../getting-started.md](../getting-started.md).
2. A recent runtime for the language you prefer.

## Configuration

Each language folder ships a `.env.example`. Copy to `.env` and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |
| `PORT`             | no | `3000` | `8080` |

## Run it

All three implementations serve the same form at `http://localhost:<PORT>/`. Start the server, open the URL, fill in the form, submit — you will be redirected to the new pedigree on Evagene.

The demo deliberately does not ship an **R** implementation — a web form is not idiomatic R territory.

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
$env:PORT = "3000"
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...
export PORT=3000

# Run the server
python -m family_intake
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
$env:PORT = "3000"
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...
export PORT=3000

# Run the server
npm start
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

### Run it in .NET 8+

```bash
cd dotnet

# Restore NuGet packages
dotnet restore

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
$env:PORT = "3000"
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...
export PORT=3000

# Run the server
dotnet run --project src/FamilyIntake
```

Run the tests (optional):

```bash
dotnet test
```

## Expected flow

1. `GET /` — renders the form.
2. User fills it in and clicks **Create pedigree**.
3. `POST /submit` — server validates, then:
   - creates the pedigree with `display_name = "<proband name>'s family"`;
   - creates the proband individual and adds them to the pedigree;
   - marks the proband (`PATCH /api/individuals/{id} { "proband": 1 }`);
   - calls `/register/add-relative` for each filled-in relative, in parent-before-grandchild order so every `relative_of` resolves.
4. On success, the browser is redirected to `<EVAGENE_BASE_URL>/pedigrees/<new-id>` so the clinician lands on the pedigree in Evagene, ready to annotate.

If anything fails, the user sees an error page naming the step that failed (e.g. *"Evagene rejected the add-relative call for the maternal grandmother"*). No partial pedigrees are surfaced — the ID of the partially-built pedigree is also shown so it can be cleaned up or resumed in the web app.

## Architecture (identical in every language)

```
  HTML form (GET /)
         │
         │  POST /submit
         ▼
  IntakeSubmission.parse (pure)
         │
         ▼
  IntakeService.create
         │
         ├─► EvageneClient.createPedigree
         ├─► EvageneClient.createIndividual       (proband)
         ├─► EvageneClient.addIndividualToPedigree
         ├─► EvageneClient.designateAsProband
         └─► EvageneClient.addRelative            (per relative, in order)
                          │
                          ▼
                    HttpGateway (abstraction)
```

- **IntakeSubmission** — value object + parser; enforces "proband name is required" and catches malformed year values. Pure, no I/O.
- **EvageneClient** — narrowly-scoped REST client; each method wraps one Evagene endpoint. Depends on `HttpGateway`.
- **IntakeService** — orchestrator; no HTTP knowledge, only calls `EvageneClient`. Pure (given a fake client).
- **Server** — Express / Flask / ASP.NET thin layer: routes `GET /`, `POST /submit`; delegates everything to `IntakeService`.
- **App** — composition root; wires concretes to abstractions.

Every file has one responsibility; every function one level of abstraction.

## Caveats

- The intake form is a **structural capture tool**, not a replacement for a clinical family-history interview. Don't use it as the only channel for gathering family history in a clinical setting.
- Years of birth are treated as public, low-sensitivity data. If you deploy this form against real patient input, add consent copy and make sure the connection to your Evagene instance is TLS-terminated.
- This is an example integration, not a validated clinical tool. Clinical governance applies.
