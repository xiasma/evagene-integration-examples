# Couple carrier risk

**Point this at two 23andMe raw genotype files — one per reproductive partner — and it prints a per-disease couple-offspring-risk table in under a minute.** The demo uploads each partner into a disposable [Evagene](https://evagene.net) pedigree, fetches their ancestry-conditioned carrier-frequency summaries, and combines them into one row per autosomal-recessive or X-linked-recessive disease, including a genuine cross-partner estimate when both carrier frequencies are known.

Useful when a reproductive-medicine clinician or IVF coordinator is holding two genotype downloads and wants a quick triage before ordering a formal expanded carrier panel.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to work against. Every demo assumes that is done.

---

## Who this is for

- **Reproductive-medicine genetic counsellors** screening a couple ahead of an IVF / PGT-M decision and wanting a reproducible first pass.
- **IVF clinic coordinators** triaging couples whose direct-to-consumer genotypes are the only data at hand before ordering a validated panel.
- **Carrier-screening programmes** prototyping the workflow before committing to a specific laboratory partner.
- **Developers** who want a worked example of Evagene's 23andMe raw import plus the ancestry-gated `population-risks` endpoint.

## What Evagene surface this uses

- **REST API** — four endpoints:
  - `POST /api/pedigrees` to spin up a scratch workspace;
  - `POST /api/individuals` + `POST /api/pedigrees/{id}/individuals/{individual_id}` to create each partner;
  - `POST /api/pedigrees/{id}/import/23andme-raw?individual_id=...` to upload each raw genotype TSV;
  - `GET /api/individuals/{id}/population-risks` to pull the ancestry-conditioned carrier-frequency table;
  - `DELETE /api/pedigrees/{id}` and `DELETE /api/individuals/{id}` to tidy up afterwards.
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scopes `read` and `write` are both needed (the import writes; the risk pull reads).
- **Interactive reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) / [https://evagene.net/redoc](https://evagene.net/redoc).

## Prerequisites

1. An Evagene account with an API key scoped for `read` + `write` — see [getting-started.md](../getting-started.md).
2. Two 23andMe raw genotype downloads — one per partner. The demo ships small synthetic fixtures under `fixtures/` that exercise every code path.
3. A recent runtime for whichever language you prefer. Only one is needed.

## Configuration

Every language reads the same environment variables. Each language folder ships a `.env.example` (Python) or `.Renviron.example` (R) you can copy and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | —                     | `evg_...` |

## Command-line contract

Both implementations accept the same invocation:

```
couple-carrier-risk --partner-a <file> --partner-b <file> \
    [--ancestry-a <key>] [--ancestry-b <key>] \
    [--output table|csv|json] [--cleanup|--no-cleanup]
```

- `--partner-a`, `--partner-b` — paths to each partner's 23andMe raw genotype TSV. Required.
- `--ancestry-a`, `--ancestry-b` — optional population keys from Evagene's ancestry catalogue (e.g. `ashkenazi_jewish`, `mediterranean`, `general`). Default `auto`, which defers to Evagene's own ancestry inference. Use `GET /api/ancestries` to list available keys.
- `--output` — one of `table` (default, aligned columns), `csv`, or `json`.
- `--cleanup` / `--no-cleanup` — delete the scratch pedigree and individuals after the run. Default `--cleanup` so the demo never leaves test data on your account. Pass `--no-cleanup` if you want to inspect the scratch pedigree in the Evagene web UI.

### Exit codes

| Code | Meaning |
|---|---|
| `0`  | Both partners screened; output written. |
| `64` | Usage error (missing / malformed arguments, unreadable 23andMe file, unknown ancestry key). |
| `69` | Evagene API call failed (HTTP non-2xx, network error, invalid JSON). |
| `70` | A population-risks response did not match the documented schema. |

## One-line run per language

Work from the language-specific subfolder. Both expect `EVAGENE_API_KEY` to be set in the environment (either exported or via `.env` / `.Renviron`).

| Language | First-time setup | Run |
|---|---|---|
| **Python 3.11+** | `python -m venv .venv` · (activate) · `pip install -e .[dev]` | `python -m couple_carrier_risk --partner-a ../fixtures/partner-a-23andme.txt --partner-b ../fixtures/partner-b-23andme.txt` |
| **R 4.3+** | `R -e 'install.packages(c("httr2","jsonlite","testthat"))'` | `Rscript inst/bin/couple-carrier-risk.R --partner-a ../fixtures/partner-a-23andme.txt --partner-b ../fixtures/partner-b-23andme.txt` |

## Expected output

The `table` format prints one row per disease appearing in either partner's risk response. Columns show each partner's ancestry-weighted carrier frequency, the API's same-ancestry `couple_offspring_risk` (assuming an untested partner of the same ancestry), and the cross-partner per-pregnancy affected-child probability computed from both frequencies:

```
Disease              Inheritance          CF(A)    CF(B)    API couple risk (A)  API couple risk (B)  Cross-partner offspring risk
Sickle cell anaemia  autosomal_recessive  7.0000%  5.0000%  0.1225%              0.0625%              0.0875%
```

`csv` emits the same content as RFC-4180 lines; `json` emits `{ "columns": [...], "rows": [{...}, ...] }` with numbers preserved as numbers and missing cells as `null`.

## Architecture

```
  CLI args + env
        │
        ▼
     Config                          GenomeFile (pure: parse + sex inference)
        │                                │
        ▼                                │
   Orchestrator ────────────────────────┘
        │
        ├─ EvageneClient (create_pedigree / create_individual /
        │                 add_individual_to_pedigree / import_23andme_raw /
        │                 add_ancestry_to_individual / get_population_risks /
        │                 delete_individual / delete_pedigree)
        │                   │
        │                   ▼
        │           HttpGateway (httpx / httr2) — tests inject a fake
        │
        ├─ couple_risk_calculator (pure: two PopulationRisks -> CoupleRow[])
        │
        ▼
    Presenter (table | csv | json)  →  stdout
```

- **Config** — immutable value object; validates env vars, output format, and required CLI flags.
- **GenomeFile** — pure: reads the TSV, checks it has genotype rows, infers biological sex from Y-chromosome calls (male if any Y row has a real genotype; female if every Y row is `--`; unknown if there are no Y rows). The file content is sent verbatim to Evagene — this module never reinterprets genotypes.
- **EvageneClient** — narrow wrapper around the handful of REST endpoints this demo needs. Raises `ApiError` with the URL in the message so a debugging reader is never left guessing.
- **HttpGateway** — single-seam abstraction over HTTP (httpx in Python, httr2 in R). Tests substitute a recording fake.
- **couple_risk_calculator** — pure transform. For each disease present in either partner's response it emits a row; for AR diseases with both frequencies known it computes `cf_a * cf_b / 4`; for XLR it uses `cf_female / 4` (the father's carrier state is irrelevant). Unknown frequencies carry through as `null` / `NULL` rather than fabricated zeros.
- **Orchestrator** — composes everything. It owns the lifetime of the scratch pedigree and individuals; cleanup runs in `finally` / `on.exit` so a failed import never leaves detritus on your account.
- **App** — thin composition root; maps exceptions to exit codes.

## Test fixtures

- `fixtures/partner-a-23andme.txt`, `fixtures/partner-b-23andme.txt` — two small synthetic 23andMe raw TSVs with ~25 SNPs covering every clinical-SNP code path the API exercises, plus a handful of Y-chromosome rows so sex inference has something to work with. Partner A's Y rows carry calls (male); partner B's are all `--` (female).
- `fixtures/sample-population-risks.json` — a realistic `GET /api/individuals/{id}/population-risks` response (sickle cell, cystic fibrosis, DMD) for the unit tests.

All fixtures are synthetic. **No real genotypes are included. Do not commit real 23andMe downloads to this repository.**

## Caveats

- This is an **illustrative example**, not a validated carrier-screening tool. Clinical decisions must go through the usual multidisciplinary governance — direct-to-consumer genotypes are screening hints, not diagnoses.
- 23andMe raw files cover only a pre-selected set of clinically-reported SNPs. Most AR carrier-screening panels cover hundreds of genes not on the 23andMe chip; a "no carrier rows" result from this demo does **not** mean a couple has no reproductive genetic risk.
- The cross-partner refinement (`cf_a * cf_b / 4` for AR, `cf_female / 4` for XLR) is the textbook Hardy-Weinberg estimate and ignores mutation heterogeneity, consanguinity, and incomplete panel detection. The Evagene `population-risks` response includes `panel_detection_rate` and `residual_carrier_frequency` for diseases where that refinement is available — see `fixtures/sample-population-risks.json` for the shape.
- The `/api/individuals/{id}/population-risks` endpoint is **ancestry-gated**: if the individual has no recorded ancestries, it returns an empty list with an explanatory message rather than a misleading global number. Run with `--ancestry-a` / `--ancestry-b` set to an explicit population key when you want reproducible results, or rely on Evagene's `auto` inference when the 23andMe data carries ancestry hints.
- The demo creates and deletes scratch data on your Evagene account. Pedigree deletion is soft (it moves to trash); individual deletion is hard. Pass `--no-cleanup` to inspect the scratch pedigree in the web UI before it is tidied.
