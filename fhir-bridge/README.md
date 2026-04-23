# fhir-bridge

Round-trip a family-history pedigree between Evagene and any FHIR R5 server: push an Evagene pedigree out as a Bundle of `FamilyMemberHistory` resources, or pull such a Bundle back and reconstruct the pedigree. One command per direction.

> **Before you start:** read [`../getting-started.md`](../getting-started.md). It covers Evagene registration, API-key minting, and the two environment variables this demo reads. Everything below assumes you have done that.

## Who this is for

- **Hospital IT teams** wiring Evagene into an EHR or shared patient record and needing the family history to flow in both directions.
- **Integration engineers** evaluating Evagene against their FHIR estate who want a short, honest demonstration of what round-trips cleanly and what does not.
- **Clinical informaticians** who need a starting point for their own mapping conventions.

## Which Evagene surfaces it uses

- **REST API** (`https://evagene.net/api/*`) — `GET /api/pedigrees/{id}`, `POST /api/pedigrees`, `POST /api/individuals`, `POST /api/pedigrees/{id}/individuals/{individual_id}`, `PATCH /api/individuals/{id}`, `POST /api/pedigrees/{id}/register/add-relative`, `DELETE /api/pedigrees/{id}` (cleanup only).

Full reference: [`https://evagene.net/docs`](https://evagene.net/docs).

On the FHIR side, the demo targets [`FamilyMemberHistory`](https://hl7.org/fhir/R5/familymemberhistory.html) (R5) via the standard `GET [base]/FamilyMemberHistory?patient=...` and `POST [base]` (transaction Bundle) interactions.

## Prerequisites

- An Evagene account plus an API key with `read` and `write` scopes. `read` alone is enough for `push`; `pull` needs `write`.
- A running FHIR R5 server you can point the demo at. Any compliant implementation works; the demo has been exercised against an in-process simulator in the test suite.
- Runtime:
  - **Node**: Node.js 20.10 or newer.
  - **.NET**: .NET SDK 8.0 or newer.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `EVAGENE_API_KEY` | yes | The `evg_...` key you created in *Getting started*. |
| `EVAGENE_BASE_URL` | no | Defaults to `https://evagene.net`. |

The FHIR server URL and optional authorisation header are passed on the command line, because a site's FHIR endpoint and credentials belong with the command, not in a checked-in `.env`.

## CLI

```
fhir-bridge push <pedigree-id>      --to   <fhir-base-url> [--auth-header <header>]
fhir-bridge pull <fhir-patient-id>  --from <fhir-base-url> [--auth-header <header>]
```

- `push`: fetches the Evagene pedigree, derives each relative's relation to the proband, maps every relative to a `FamilyMemberHistory` resource, and POSTs them as a transaction `Bundle`. The new FHIR resource IDs are printed one per line.
- `pull`: issues `GET /FamilyMemberHistory?patient={patient-id}`, maps the returned entries into a proband-plus-relatives shape, and creates a fresh Evagene pedigree. The new Evagene pedigree ID is printed on the last line.

The `--auth-header` flag takes the literal value of an HTTP header (for example, `Authorization: Bearer eyJ...`) and is forwarded verbatim to the FHIR server. Omit it for open FHIR endpoints.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. |
| 64 | Usage / argument / configuration error. |
| 69 | Network or HTTP failure against Evagene or the FHIR server. |
| 70 | Mapping error (unrecognised FHIR shape or missing required field). |

### Run it

Both implementations expect `EVAGENE_API_KEY` to be set in the environment. The FHIR server URL and optional auth header are passed on the command line, not via env.

#### Run it in Node 20+

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
npm start -- push <pedigree-id> --to https://fhir.example/fhir
```

Run the tests (optional):

```bash
npm test
npm run lint
npm run typecheck
```

#### Run it in .NET 8+

```bash
cd dotnet

# Restore NuGet packages
dotnet restore

# Set your Evagene API key (one shell session)
# Windows PowerShell:
$env:EVAGENE_API_KEY = "evg_..."
# macOS / Linux (bash / zsh):
export EVAGENE_API_KEY=evg_...

# Run the demo
dotnet run --project src/FhirBridge -- push <pedigree-id> --to https://fhir.example/fhir
```

Run the tests (optional):

```bash
dotnet test
```

### Expected output

```
$ fhir-bridge push 7c8d4d6a-... --to https://fhir.example/fhir
POST Bundle  -> 201 Created
FamilyMemberHistory/fmh-001  (mother)
FamilyMemberHistory/fmh-002  (father)
FamilyMemberHistory/fmh-003  (maternal_grandmother)
...
wrote 7 FamilyMemberHistory resources

$ fhir-bridge pull patient-42 --from https://fhir.example/fhir
GET  FamilyMemberHistory?patient=patient-42  -> 200 OK (7 entries)
pedigree created: a4c1e8ab-12cd-4ef0-9abc-1234567890ab
proband:          8f2c9a01-1111-2222-3333-444455556666
relatives added:  7
```

## Architecture

Both implementations share the same split:

```
CLI args + env ──> Config
                      │
                      ▼
                    App ────────────────┐
                      │                 │
                      ▼                 ▼
            EvageneClient          FhirClient
                      │                 │
                      ▼                 ▼
                         HttpGateway (shared abstraction)
```

Pure transformers sit either side of the clients:

- `pedigree_to_fhir` (Node) / `PedigreeToFhir` (.NET) — takes a `PedigreeDetail` document and returns a FHIR `Bundle`.
- `fhir_to_intake` (Node) / `FhirToIntake` (.NET) — takes a FHIR `Bundle` and returns a flat `ExtractedFamily` which `IntakeService` turns into Evagene calls.

Relation lookups are a single table; see `relationMap` in each language. Unknown FHIR relationship codes are logged as warnings and their resources are skipped.

## Relation mapping

| FHIR code (HL7 v3 RoleCode) | Evagene `relative_type` |
|---|---|
| `MTH` | `mother` |
| `FTH` | `father` |
| `BRO` | `brother` |
| `SIS` | `sister` |
| `HBRO` | `half_brother` |
| `HSIS` | `half_sister` |
| `MGRMTH` | `maternal_grandmother` |
| `MGRFTH` | `maternal_grandfather` |
| `PGRMTH` | `paternal_grandmother` |
| `PGRFTH` | `paternal_grandfather` |
| `SON` | `son` |
| `DAU` | `daughter` |
| `MAUNT` | `maternal_aunt` |
| `MUNCLE` | `maternal_uncle` |
| `PAUNT` | `paternal_aunt` |
| `PUNCLE` | `paternal_uncle` |
| `NIECE` | `niece` |
| `NEPH` | `nephew` |
| `COUSN` | `first_cousin` |

The table is reversible. Codes not listed are skipped with a warning.

## Caveats

- **Lossy mapping.** FHIR `FamilyMemberHistory.relationship` uses broad SNOMED / v3 codes that do not always pin down sidedness or half/full degree. Unknown or ambiguous codes are skipped; this demo does not invent a relation it cannot prove.
- **No FHIR extensions.** Evagene-specific fields that do not map cleanly into `FamilyMemberHistory` (consanguinity, ancestry, monozygotic-twin marker, adopted/fostered flags, pedigree coordinates) are *not* carried across. Treat the bridge as a floor, not a ceiling.
- **Consent and privacy.** `FamilyMemberHistory` contains sensitive third-party information. The demo does not assert any basis for sharing; run it only against endpoints you are authorised to write to, and keep your `--auth-header` value out of shell history.
- **FHIR R5 only.** The demo is pinned to the R5 release (`https://hl7.org/fhir/R5`). Earlier releases use a different `relationship` cardinality and are not supported.
- **Not a validated clinical tool.** These are illustrative integrations. Any clinical use must go through normal governance.

## Fixtures

- `fixtures/sample-evagene-detail.json` — a realistic `PedigreeDetail` response used by the transformer tests and the in-process round-trip integration test.
- `fixtures/sample-fhir-bundle.json` — a realistic FHIR R5 `Bundle` of `FamilyMemberHistory` entries, used the other way round.
