# Notebook explorer

**Drive Evagene's risk engine from a notebook and watch the numbers move.** Open the notebook, pick a pedigree from your Evagene account, and explore how the risk outputs shift as you vary inputs: add an affected relative, step through Tyrer-Cuzick reproductive-history fields, or turn the Falconer heritability knob on a multifactorial model. Two kernels, one narrative.

Built for people who learn and teach by poking at a model:

- **Researchers** writing a methods paper — "risk under varied assumptions" is the whole section, and a notebook is the right artefact.
- **Educators** teaching liability-threshold intuition or the structure of family-history criteria — sliders make the abstract concrete.
- **Anyone** wanting a runnable reference for how Evagene's risk outputs shift under what-if inputs, without wiring up a UI.

> **New to Evagene integrations?** Start with **[../getting-started.md](../getting-started.md)** — it covers registering at [evagene.net](https://evagene.net), minting an API key, and picking a pedigree to try the demos against.

---

## What Evagene surfaces this uses

- **REST API** — `POST /api/pedigrees/{id}/risk/calculate` (NICE, TYRER_CUZICK, MULTIFACTORIAL, repeatedly with varied inputs), `GET /api/pedigrees` (list), `POST /api/pedigrees` + `GET .../export.ged` + `POST .../import/gedcom` (clone via GEDCOM round-trip), `POST .../register/add-relative`, `POST /api/individuals/{id}/diseases`, `DELETE /api/pedigrees/{id}` (scratch cleanup).
- **Authentication** — long-lived API key via `X-API-Key: evg_...`. Scopes `read` + `write` + `analyze`.
- **Interactive API reference** — [https://evagene.net/docs](https://evagene.net/docs) (Swagger) or [https://evagene.net/redoc](https://evagene.net/redoc).

## What the notebook covers

Both the Jupyter (Python) and Quarto (R) variants follow the same seven-section arc:

1. **Setup** — load env, build the client.
2. **Pick a pedigree** — list your pedigrees as a markdown table; choose one.
3. **Baseline NICE category** — green / amber / red on the unmodified family.
4. **What if we add an affected sister?** — clone the pedigree into a scratch copy, add a sister affected with breast cancer, re-run NICE, watch the category tick up. The scratch pedigree is deleted at the end of the notebook.
5. **Tyrer-Cuzick slider** — vary `age_at_menarche`, `parity`, `breast_density_birads`; chart the 10-year-risk surface.
6. **Multifactorial under varied heritability** — liability-threshold intuition; chart recurrence risk against h².
7. **Caveats and suggested reading.**

## Prerequisites

1. An Evagene account and an API key with `read` + `write` + `analyze` scopes — see [getting-started.md](../getting-started.md). `write` is needed because the notebook creates a scratch pedigree clone for the "add an affected sister" section.
2. At least one pedigree on your account, ideally with a designated female proband who has reproductive-history fields set (age at menarche, parity) — otherwise the Tyrer-Cuzick section returns sparse results.
3. A runtime for the kernel you prefer — only one is required.

## Configuration

Both kernels read the same environment variables. Each language folder ships a `.env.example` (Python) or `.Renviron.example` (R) you can copy and fill in.

| Variable | Required | Default | Example |
|---|---|---|---|
| `EVAGENE_BASE_URL` | no | `https://evagene.net` | `https://evagene.net` |
| `EVAGENE_API_KEY`  | yes | — | `evg_...` |

## One-line run per kernel

Work from the language-specific subfolder.

| Kernel | First-time setup | Run |
|---|---|---|
| **Python 3.11+ / Jupyter** | `python -m venv .venv` · (activate) · `pip install -e .[dev]` | `jupyter lab explorer.ipynb` (interactive) or `jupyter nbconvert --execute --to notebook --inplace explorer.ipynb` (headless) |
| **R 4.3+ / Quarto 1.4+**   | `R -e 'install.packages(c("httr2","jsonlite","ggplot2","knitr","testthat","rmarkdown"))'` | `quarto render explorer.qmd` (renders to `explorer.html`) or `quarto preview explorer.qmd` (interactive). If Quarto is not installed, `Rscript _render_fallback.R` produces the same `explorer.html` via `rmarkdown`. |

The notebook saves its executed outputs so a GitHub preview renders charts and tables without a runtime.

## What you should see

- Section 2 — a table of your pedigrees with a direct link back to each one at `https://evagene.net/pedigrees/<uuid>`.
- Section 3 — a single-line verdict: `MODERATE (amber) — triggers: [...]`.
- Section 4 — the same verdict *before* and *after* the synthetic sister is added; expect NICE to tick up if the chosen proband is female and has a breast-cancer disease in the pedigree working set.
- Section 5 — a line plot of Tyrer-Cuzick 10-year risk versus age at menarche (one line per parity value).
- Section 6 — a line plot of multifactorial recurrence risk versus heritability.

## Scratch-pedigree cleanup

Section 4 clones the chosen pedigree into a short-lived copy named `"[scratch] notebook-explorer YYYY-MM-DD HH:MM"` and deletes it in the closing cell. **If the notebook crashes mid-run, the scratch clone may persist.** To find and delete orphaned scratch pedigrees:

1. Open [https://evagene.net](https://evagene.net) and look for any pedigree whose name starts with `[scratch] notebook-explorer`.
2. Delete it from the UI, or call `DELETE /api/pedigrees/{id}` with your API key.

The clone is created in your account and counts against your quota until deleted.

## Architecture (identical in both kernels)

```
  Notebook cells
        │
        ▼
   Config (env)  →  HttpGateway (thin)  →  EvageneClient
                                                │
                   ┌────────────────────────────┼────────────────────────────┐
                   ▼                            ▼                            ▼
            get_pedigrees()             run_risk(pedigree_id,       clone_pedigree_for_exploration()
                                          model, **body)            delete_pedigree(id)
```

- **HttpGateway** — narrow abstraction the tests fake.
- **EvageneClient** — five tiny methods. Nothing clever; the readable cell is the point.
- **Notebook** — the demo itself. Helpers stay out of the way.

## Tests

Per kernel:

- **Client unit tests** — fake gateway, round-trip each client method, verify the clone sequence issues the expected POST / GET / POST / POST calls in order.
- **Notebook smoke test (primary)** — `jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=120 explorer.ipynb` (Python) or `quarto render explorer.qmd` (R) against a real Evagene account. Both create, use, and delete a scratch pedigree in a single run.

## Caveats

- **Interactive cells mutate a scratch clone, never your original pedigree.** The clone is deleted in the closing cell.
- **If the notebook aborts before the closing cell, the scratch clone survives** — delete it manually (see above).
- **Tyrer-Cuzick** is an IBIS-style approximation, not the licensed IBIS tool. **BOADICEA** is not bundled with Evagene; export a CanRisk v2 file and upload at [canrisk.org](https://canrisk.org) for the full multi-gene / PRS calculation.
- **Multifactorial recurrence risk** here is Evagene's Falconer liability-threshold output (with Carter-effect and consanguinity modifiers); it is not a substitute for a published empirical recurrence-risk table for the specific condition.
- These are example integrations, not validated clinical tools. Clinical decisions should go through the usual multidisciplinary governance.

## Suggested reading

- Falconer DS. *Ann Hum Genet* 1965 — liability-threshold model underpinning the multifactorial section.
- Tyrer J, Duffy SW, Cuzick J. *Stat Med* 2004 — the IBIS breast-cancer risk model.
- NICE CG164 / NG101 — family-history triage rules driving the NICE category shown in the baseline section.
