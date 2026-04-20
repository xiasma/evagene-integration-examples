"""Clinical caveat sentences, keyed by risk-model name.

The copy here is non-negotiable — it is the text the clinician signs
off when they distribute the briefing. If you are tempted to shorten
it, do not: clinical governance depends on the caveats being present,
verbatim, on every case.

All sentences are in British English. Footer / boilerplate strings are
returned as a tuple so callers cannot mutate shared state.
"""

from __future__ import annotations

FOOTER_CAVEAT = (
    "Not a validated clinical tool \u2014 clinical governance applies."
)

GENERAL_CAVEATS: tuple[str, ...] = (
    "This briefing summarises computed risk estimates for discussion at an "
    "oncology MDT / tumour board. It is not a substitute for formal "
    "genetics assessment, counselling, or a clinician's direct review of "
    "the pedigree.",
    "Every model below is driven by the family history recorded in Evagene "
    "at the time of rendering. If the recorded history is incomplete, "
    "inconsistent, or based on self-report without documentary verification, "
    "the outputs will inherit those limitations.",
    "The risk figures are illustrative integrations of published models, "
    "not clinically validated outputs. Clinical governance applies to any "
    "decision made in light of this briefing.",
)

_CAVEATS_BY_MODEL: dict[str, tuple[str, ...]] = {
    "CLAUS": (
        "Claus lifetime breast-cancer risk (Claus, Risch & Thompson 1991 / "
        "1994) is derived from the CASH study tables and is driven purely "
        "by the number, relationship, and age at diagnosis of affected "
        "relatives. It does not account for genetic-test results, "
        "reproductive history, or breast density.",
    ),
    "COUCH": (
        "Couch BRCA1 probability (Couch et al. 1997) is a logistic "
        "regression over average age at breast-cancer diagnosis, ovarian "
        "cancer in the family, and Ashkenazi-Jewish ancestry. It predates "
        "multi-gene panel testing and does not model BRCA2 or other "
        "susceptibility genes.",
    ),
    "FRANK": (
        "Frank / Myriad empirical tables (Frank et al. 2002) return the "
        "population frequency of a detectable BRCA1 / BRCA2 mutation for "
        "the closest-matching canonical family-history scenario. Pedigrees "
        "that do not match a canonical scenario fall back to a low-prior "
        "estimate.",
    ),
    "MANCHESTER": (
        "Manchester Scoring System (Evans et al. 2004, updated 2017) gives "
        "separate BRCA1 and BRCA2 point scores. A BRCA1 or BRCA2 score of "
        "16 or more corresponds to approximately a 10% carrier probability; "
        "a combined score of 20 or more corresponds to approximately 20%. "
        "Only the proband and first- or second-degree relatives on the same "
        "side of the family contribute to the score.",
    ),
    "NICE": (
        "NICE CG164 / NG101 (updated 2023) categorises familial breast-cancer "
        "risk by family-history structure rather than by a continuous "
        "lifetime-risk estimate. Near-population corresponds to a lifetime "
        "risk below 17%, moderate to 17-30%, and high to 30% or more. The "
        "category is only one input into the referral decision; the specific "
        "triggers matter.",
    ),
    "TYRER_CUZICK": (
        "Tyrer-Cuzick output is an IBIS-style approximation of the published "
        "Tyrer, Duffy & Cuzick 2004 model and subsequent public updates. It "
        "is not the official IBIS Breast Cancer Risk Evaluator. For a "
        "fully-validated run, export the pedigree as a ##CanRisk 2.0 "
        "pedigree file and upload it at canrisk.org.",
    ),
}

GLOBAL_MODEL_CAVEATS: tuple[str, ...] = (
    "BOADICEA is not bundled with Evagene. For a full BOADICEA / CanRisk "
    "assessment with multi-gene carrier probabilities, polygenic risk "
    "scores, and mammographic density, export the pedigree as a "
    "##CanRisk 2.0 file from Evagene and upload it at canrisk.org.",
)


def caveats_for(model: str) -> tuple[str, ...]:
    """Return the caveat sentences for a single model, or an empty tuple
    if the model is not covered here.
    """
    return _CAVEATS_BY_MODEL.get(model, ())


def caveats_for_models(models: tuple[str, ...]) -> tuple[str, ...]:
    """Concatenate the caveats for every model in ``models`` in order,
    then append the global model caveats.
    """
    out: list[str] = []
    for model in models:
        out.extend(caveats_for(model))
    out.extend(GLOBAL_MODEL_CAVEATS)
    return tuple(out)
