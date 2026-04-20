"""Author the ``explorer.ipynb`` notebook in code.

Hand-editing JSON is error-prone and reviewers would rather read Python,
so this script emits the canonical notebook from an ordered list of
(kind, source) tuples.  Run it whenever the notebook narrative changes;
commit the generated ``.ipynb`` (with executed outputs) alongside.

Run from the ``python/`` directory:

    python _build_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK_PATH = Path(__file__).parent / "explorer.ipynb"


def md(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


CELLS: list[dict] = [
    md(
        """# Evagene risk explorer (Python / Jupyter)

A **what-if** tour of Evagene's risk outputs — one cell per question, one
chart per answer. Pick a pedigree from your account and step through:

1. **Setup** — load the API key from the environment.
2. **Pick a pedigree** — choose the family to work with.
3. **Baseline NICE category** — green / amber / red on that family as it stands.
4. **Add an affected sister** — clone the pedigree into a scratch copy, add a
   synthetic first-degree relative with breast cancer, and re-run NICE.
5. **Tyrer-Cuzick slider** — sweep the proband's reproductive-history inputs and
   chart the 10-year / lifetime risk surface.
6. **Multifactorial under varied heritability** — Falconer liability-threshold
   intuition against several heritable diseases on the same family structure.
7. **Caveats and suggested reading.**

**The scratch pedigree is created in Section 4 and deleted in Section 7.**
If the notebook aborts mid-way, find the orphan in the Evagene web UI
(it is named `[scratch] notebook-explorer ...`) and delete it by hand."""
    ),
    md(
        """## 1. Setup

The notebook uses a small client module (`notebook_explorer.client.EvageneClient`)
whose only job is to make the cells below short. The key lives in an
environment variable — never in a cell.

> **First-time setup:** copy `.env.example` to `.env`, paste in your Evagene
> API key (scopes `read` + `write` + `analyze`), and start Jupyter from a
> shell that has that environment loaded."""
    ),
    code(
        """import os
import time
from datetime import datetime, timezone

import matplotlib.pyplot as plt

from notebook_explorer import EvageneClient, HttpxGateway, load_config

# Tolerate a ``.env`` file sitting next to this notebook (or in any
# parent directory up to the repo root) for convenience when launching
# Jupyter from outside a dotenv-aware shell.
def _load_dotenv() -> None:
    here = os.path.abspath(".")
    for _ in range(5):
        candidate = os.path.join(here, ".env")
        if os.path.exists(candidate):
            for _line in open(candidate, encoding="utf-8"):
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _, _v = _line.partition("=")
                    os.environ.setdefault(_k.strip(), _v.strip())
            return
        parent = os.path.dirname(here)
        if parent == here:
            return
        here = parent


_load_dotenv()

config = load_config(os.environ)
client = EvageneClient(
    base_url=config.base_url,
    api_key=config.api_key,
    http=HttpxGateway(),
)
print(f"Ready. Base URL: {config.base_url}")"""
    ),
    md(
        """## 2. Pick a pedigree

The list is pulled from `GET /api/pedigrees`. Each row links back to the web
UI. Copy the ID you want to explore into the cell below."""
    ),
    code(
        """from IPython.display import Markdown

pedigrees = client.get_pedigrees()

_rows = ["| # | Name | Link | ID |", "|---|---|---|---|"]
for _i, _p in enumerate(pedigrees):
    _name = _p.get("display_name") or "(untitled)"
    _pid = _p.get("id", "")
    _url = client.evagene_url(_pid)
    _rows.append(f"| {_i} | {_name} | [open]({_url}) | `{_pid}` |")

Markdown("\\n".join(_rows))"""
    ),
    md(
        """Set `PEDIGREE_ID` below to the UUID of the pedigree you want to
explore. The default points at the first pedigree on the account — swap it
for a family with an affected breast-cancer relative if you want the NICE /
Tyrer-Cuzick sections to produce the most interesting numbers."""
    ),
    code(
        """# Default: prefer a pedigree whose display_name mentions "breast" (so
# the NICE and Tyrer-Cuzick sections produce meaningful numbers); fall
# back to the first pedigree otherwise.  Override by setting PEDIGREE_ID
# to any UUID from the table above.
selected = next(
    (p for p in pedigrees
     if "breast" in (p.get("display_name") or "").lower()),
    pedigrees[0],
)
PEDIGREE_ID = selected["id"]
print(f"Selected: {selected.get('display_name')}")
print(f"Link:     {client.evagene_url(PEDIGREE_ID)}")"""
    ),
    md(
        """## 3. Baseline NICE category

One call to `POST /api/pedigrees/{id}/risk/calculate` with `model=NICE`.
The response carries `cancer_risk.nice_category` (one of `near_population`,
`moderate`, `high`), the triggers that fired, and human-readable notes."""
    ),
    code(
        """_TRAFFIC_LIGHTS = {
    "near_population": "GREEN",
    "moderate": "AMBER",
    "high": "RED",
}


def summarise_nice(payload: dict) -> str:
    cr = payload.get("cancer_risk") or {}
    category = cr.get("nice_category", "unknown")
    triggers = cr.get("nice_triggers") or []
    notes = cr.get("notes") or []
    light = _TRAFFIC_LIGHTS.get(category, "unknown")
    lines = [f"NICE category: {category.upper()} ({light})"]
    lines.append(f"Triggers: {list(triggers) if triggers else 'none'}")
    if notes:
        lines.append(f"Note: {notes[0]}")
    return "\\n".join(lines)


baseline_nice = client.run_risk(PEDIGREE_ID, "NICE")
print(summarise_nice(baseline_nice))"""
    ),
    md(
        """## 4. What if we add affected first-degree relatives?

This is where the scratch clone comes in. The notebook:

1. Clones the pedigree via a GEDCOM round-trip (export → create → import).
2. Adds a synthetic sister to the proband; flags the sister and (if present)
   the mother affected with breast cancer.
3. Re-runs the NICE calculation on the scratch copy.

Two affected first-degree relatives is the textbook NICE "moderate"
(amber) trigger. The original pedigree is never touched. The clone is
deleted in the closing cell (Section 7)."""
    ),
    code(
        """_suffix = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
SCRATCH_ID = client.clone_pedigree_for_exploration(
    PEDIGREE_ID, scratch_suffix=_suffix,
)
print(f"Scratch pedigree: {client.evagene_url(SCRATCH_ID)}")"""
    ),
    code(
        """# We need the scratch proband's ID and a \"Breast Cancer\" disease ID.
# The register endpoint gives us the proband; we look up the breast-cancer
# disease by display name in the disease catalogue so the demo works
# regardless of which diseases were attached to the pedigree you picked.
import httpx

register = client.get_register(SCRATCH_ID)
proband_id = register.get("proband_id")
print(f"Scratch proband: {proband_id}")

_disease_catalogue = httpx.get(
    f"{config.base_url}/api/diseases",
    headers={"X-API-Key": config.api_key, "Accept": "application/json"},
    timeout=30,
).json()
breast_cancer = next(
    (d for d in _disease_catalogue
     if (d.get("display_name") or "").strip() == "Breast Cancer"),
    None,
)
if breast_cancer is None:
    raise RuntimeError("No 'Breast Cancer' disease in your catalogue; cannot continue section 4.")
BREAST_CANCER_ID = breast_cancer["id"]
print(f"Breast Cancer disease id: {BREAST_CANCER_ID}")
client.add_disease_to_pedigree(SCRATCH_ID, BREAST_CANCER_ID)"""
    ),
    code(
        """# Add an affected sister.  The new individual is returned with her ID.
sister = client.add_relative(
    SCRATCH_ID,
    relative_of=proband_id,
    relative_type="sister",
    display_name="Synthetic sister",
    biological_sex="female",
)
sister_id = sister["individual"]["id"]
print(f"Sister id: {sister_id}")

client.add_disease_to_individual(
    sister_id,
    disease_id=BREAST_CANCER_ID,
    age_at_diagnosis=38,
)

# Also mark the mother affected (two affected first-degree relatives is
# the textbook NICE \"moderate\" trigger — one affected sister alone does
# not reliably cross the threshold for every family structure).
mother_row = next(
    (r for r in register["rows"]
     if r.get("relationship_to_proband") == "Mother"),
    None,
)
if mother_row is not None:
    client.add_disease_to_individual(
        mother_row["individual_id"],
        disease_id=BREAST_CANCER_ID,
        age_at_diagnosis=45,
    )
    print("Marked sister and mother affected with Breast Cancer.")
else:
    print("Marked sister affected with Breast Cancer (no mother in the pedigree).")"""
    ),
    code(
        """after_nice = client.run_risk(SCRATCH_ID, "NICE")
print("BEFORE:")
print(summarise_nice(baseline_nice))
print()
print("AFTER:")
print(summarise_nice(after_nice))"""
    ),
    md(
        """## 5. Tyrer-Cuzick slider

`TYRER_CUZICK` reads the **proband's** reproductive-history fields:
`age_at_menarche`, `parity`, `age_at_first_live_birth`,
`breast_density_birads` (BI-RADS 1–4), `hormone_therapy_years`, and so on.
They live on the individual record, not the risk-request body — so this
section mutates them on the scratch proband and re-runs TC for each
combination.

The request rate is held below the 60-per-minute server limit with a small
pause between calls."""
    ),
    code(
        """MENARCHE_AGES = (10, 13)
PARITIES = (0, 2)
BIRADS_LEVELS = (1, 2, 3, 4)

results: list[dict] = []
for menarche in MENARCHE_AGES:
    for parity in PARITIES:
        for birads in BIRADS_LEVELS:
            client.patch_individual(
                proband_id,
                age_at_menarche=menarche,
                parity=parity,
                breast_density_birads=birads,
                age_at_first_live_birth=28 if parity else None,
            )
            time.sleep(0.4)  # avoid the 60/min rate limit with headroom
            tc = client.run_risk(SCRATCH_ID, "TYRER_CUZICK")
            cancer_risk = tc.get("cancer_risk") or {}
            results.append({
                "menarche": menarche,
                "parity": parity,
                "birads": birads,
                "ten_year": cancer_risk.get("tc_ten_year_risk"),
                "lifetime": cancer_risk.get("tc_lifetime_risk"),
            })

print(f"TC results: {len(results)} points")"""
    ),
    code(
        """fig, ax = plt.subplots(figsize=(8, 5))
for menarche in MENARCHE_AGES:
    for parity in PARITIES:
        xs = [r["birads"] for r in results
              if r["menarche"] == menarche and r["parity"] == parity
              and r["ten_year"] is not None]
        ys = [r["ten_year"] * 100 for r in results
              if r["menarche"] == menarche and r["parity"] == parity
              and r["ten_year"] is not None]
        if xs:
            ax.plot(
                xs, ys, marker="o",
                label=f"menarche {menarche}, parity {parity}",
            )
ax.set_xticks([1, 2, 3, 4])
ax.set_xlabel("BI-RADS breast density (1 = almost entirely fatty, 4 = extremely dense)")
ax.set_ylabel("Tyrer-Cuzick 10-year risk (%)")
ax.set_title("Tyrer-Cuzick 10-year risk vs breast density, by reproductive history")
ax.grid(True, alpha=0.3)
ax.legend(loc="best", fontsize=9)
plt.tight_layout()
plt.show()"""
    ),
    md(
        """Reading the chart: each curve holds `age_at_menarche` and `parity`
constant while BI-RADS walks from 1 (fatty) to 4 (extremely dense). Denser
breasts drag risk up steeply; higher parity (with age at first live birth
fixed at 28) shifts the whole curve down — the classic protective effect."""
    ),
    md(
        """## 6. Multifactorial under varied heritability

The multifactorial (Falconer liability-threshold) model takes a disease's
`heritability` ($h^2$) and `population_prevalence` ($K$), plus the affected-
relative structure, and returns a recurrence risk for the proband.

`/risk/calculate` does **not** accept a request-level $h^2$ override, so to
trace the curve the notebook runs the model once per disease against the
(sister-is-affected) scratch family. Each disease is a point on the $h^2$
axis; reading risk against $h^2$ shows how the liability-threshold model
ramps up recurrence risk as heritability rises — here at fixed "one
affected first-degree relative" structure."""
    ),
    code(
        """# Pull the disease catalogue to find diseases with heritability set.
import httpx

_resp = httpx.get(
    f"{config.base_url}/api/diseases",
    headers={"X-API-Key": config.api_key, "Accept": "application/json"},
    timeout=30,
)
all_diseases = _resp.json() if _resp.status_code == 200 else []
heritable = [d for d in all_diseases if d.get("heritability")]
print(f"{len(heritable)} heritable diseases in the catalogue.")

# Pick a handful spanning the h2 range.
picks = sorted(heritable, key=lambda d: d["heritability"])
NAMES = [
    "Major Depressive Disorder (Familial)",
    "Type 2 Diabetes (Familial)",
    "Epilepsy (Familial)",
    "Cleft Lip With or Without Cleft Palate",
    "Schizophrenia (Familial)",
    "Bipolar Disorder (Familial)",
    "Coeliac Disease",
    "Ankylosing Spondylitis",
]
_by_name = {d["display_name"]: d for d in heritable}
picks = [_by_name[n] for n in NAMES if n in _by_name]
for d in picks:
    print(f"  h2={d['heritability']:.2f}  K={d.get('population_prevalence')}  {d['display_name']}")"""
    ),
    code(
        """# For each disease: add it to the scratch pedigree's working set, make the
# synthetic sister affected with it, and run MULTIFACTORIAL with the
# disease as the target.

mf_rows: list[dict] = []
for d in picks:
    did = d["id"]
    client.add_disease_to_pedigree(SCRATCH_ID, did)
    time.sleep(0.3)
    client.add_disease_to_individual(
        sister_id, disease_id=did, age_at_diagnosis=30,
    )
    time.sleep(0.3)
    out = client.run_risk(SCRATCH_ID, "MULTIFACTORIAL", disease_id=did)
    block = out.get("multifactorial") or {}
    mf_rows.append({
        "disease": d["display_name"],
        "h2": d["heritability"],
        "K": d.get("population_prevalence"),
        "final_risk": block.get("final_risk"),
        "base_risk": block.get("base_risk"),
        "base_source": block.get("base_source"),
        "nearest_class": block.get("nearest_class"),
    })

for row in mf_rows:
    print(row)"""
    ),
    code(
        """fig, ax = plt.subplots(figsize=(8, 5))
xs = [r["h2"] for r in mf_rows if r["final_risk"] is not None]
ys = [r["final_risk"] * 100 for r in mf_rows if r["final_risk"] is not None]
labels = [r["disease"] for r in mf_rows if r["final_risk"] is not None]

ax.scatter(xs, ys, s=60)
for x, y, lab in zip(xs, ys, labels, strict=True):
    ax.annotate(lab, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)

ax.set_xlabel("Disease heritability of liability (h²)")
ax.set_ylabel("Multifactorial recurrence risk for proband (%)\\n"
              "with one affected first-degree relative")
ax.set_title("Recurrence risk rises with heritability under the\\n"
             "Falconer liability-threshold model")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()"""
    ),
    md(
        """Each point is a real disease, run through Evagene's multifactorial
engine against the same synthetic family structure (one affected first-degree
relative, otherwise unaffected). Population prevalence varies across diseases
and also drives the curve — the Falconer model is a joint function of
$h^2$ and $K$, so the points do not fall on a single line. That is the
teaching point: heritability is a lever, not a knob."""
    ),
    md(
        """## 7. Caveats and cleanup

The final cell deletes the scratch pedigree. If a preceding cell raised,
run this cell manually before retrying — otherwise the scratch copy stays
in your account."""
    ),
    code(
        """client.delete_pedigree(SCRATCH_ID)
print(f"Scratch pedigree {SCRATCH_ID} deleted. Your original is untouched.")"""
    ),
    md(
        """### Caveats

- **Tyrer-Cuzick** is an IBIS-style approximation, not the licensed IBIS
  tool. **BOADICEA** is not bundled; for the full multi-gene / polygenic-
  risk-score version, export a CanRisk v2 file from the pedigree and upload
  at [canrisk.org](https://canrisk.org).
- **Multifactorial recurrence risk** shown here is Evagene's Falconer
  liability-threshold output with Carter-effect and consanguinity modifiers.
  Published empirical recurrence tables (when they exist) are a better
  source for the specific disease.
- These are example integrations, **not validated clinical tools**.

### Suggested reading

- Falconer DS. *Ann Hum Genet* 1965 — the liability-threshold foundation.
- Tyrer J, Duffy SW, Cuzick J. *Stat Med* 2004 — the IBIS breast-cancer model.
- NICE CG164 / NG101 — family-history triage rules driving the NICE category.
- Parmigiani et al. *Am J Hum Genet* 1998 — BRCAPRO, the Bayesian counterpart."""
    ),
]


def build() -> None:
    notebook = {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    print(f"Wrote {NOTEBOOK_PATH} ({len(CELLS)} cells)")


if __name__ == "__main__":
    build()
