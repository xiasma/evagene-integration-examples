"""Pure transform: per-model RiskResult payloads -> a list of ModelSummary.

Each briefing prints one row per model in the risk summary table. A
``ModelSummary`` captures the headline figure (e.g. "Lifetime 38.0%"),
an optional threshold flag, and the list of triggers / criteria met for
that model. Models the server failed to return (or rejected) surface as
a summary whose ``headline`` says so, rather than being silently dropped
— the clinician needs to know what did and did not run.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# A fetch either succeeded and produced a dict payload, or failed and
# produced an error message. Nothing else is allowed — that's why the
# type is explicit.
FetchResult = dict[str, Any] | BaseException


@dataclass(frozen=True)
class ModelSummary:
    model: str
    headline: str
    detail: str
    threshold_label: str
    triggers: tuple[str, ...]


def build_summaries(
    fetches: Mapping[str, FetchResult],
) -> tuple[ModelSummary, ...]:
    """Turn a ``{model: payload-or-error}`` mapping into a briefing-ready
    tuple of :class:`ModelSummary`.

    Key order is preserved so the caller controls table row order.
    """
    return tuple(_summarise(model, result) for model, result in fetches.items())


def _summarise(model: str, result: FetchResult) -> ModelSummary:
    if isinstance(result, BaseException):
        return ModelSummary(
            model=model,
            headline="not available",
            detail=str(result) or result.__class__.__name__,
            threshold_label="",
            triggers=(),
        )
    summariser = _SUMMARISERS.get(model)
    if summariser is None:
        return ModelSummary(
            model=model,
            headline="unsupported model",
            detail="",
            threshold_label="",
            triggers=(),
        )
    cancer_risk = result.get("cancer_risk")
    if not isinstance(cancer_risk, dict):
        return ModelSummary(
            model=model,
            headline="not available",
            detail="response did not contain a cancer_risk block",
            threshold_label="",
            triggers=(),
        )
    return summariser(model, cancer_risk)


def _summarise_claus(model: str, block: dict[str, Any]) -> ModelSummary:
    lifetime = _optional_percent(block.get("claus_lifetime_risk"))
    relative = block.get("claus_relative_risk")
    detail_parts: list[str] = []
    if isinstance(relative, int | float) and not isinstance(relative, bool):
        detail_parts.append(f"relative risk x{relative:.2f}")
    source = block.get("claus_source")
    if isinstance(source, str) and source:
        detail_parts.append(f"source: {source}")
    return ModelSummary(
        model=model,
        headline=f"Lifetime breast-cancer risk {lifetime}",
        detail="; ".join(detail_parts),
        threshold_label="",
        triggers=(),
    )


def _summarise_couch(model: str, block: dict[str, Any]) -> ModelSummary:
    probability = _optional_percent(block.get("couch_brca1_probability"))
    threshold_met = block.get("couch_threshold_met")
    threshold_label = ""
    if isinstance(threshold_met, bool):
        threshold_label = "testing threshold met" if threshold_met else "below testing threshold"
    return ModelSummary(
        model=model,
        headline=f"BRCA1 probability {probability}",
        detail="Couch 1997 logistic regression",
        threshold_label=threshold_label,
        triggers=(),
    )


def _summarise_frank(model: str, block: dict[str, Any]) -> ModelSummary:
    brca1 = _optional_percent(block.get("frank_brca1_probability"))
    brca2 = _optional_percent(block.get("frank_brca2_probability"))
    combined = _optional_percent(block.get("frank_combined_probability"))
    scenario = block.get("frank_scenario")
    detail = scenario.replace("_", " ") if isinstance(scenario, str) else ""
    return ModelSummary(
        model=model,
        headline=f"BRCA1 {brca1} / BRCA2 {brca2} / combined {combined}",
        detail=detail,
        threshold_label="",
        triggers=(),
    )


def _summarise_manchester(model: str, block: dict[str, Any]) -> ModelSummary:
    brca1 = _optional_int(block.get("manchester_brca1_score"))
    brca2 = _optional_int(block.get("manchester_brca2_score"))
    combined = _optional_int(block.get("manchester_combined_score"))
    flags = []
    if block.get("manchester_brca1_over_10pct") is True:
        flags.append("BRCA1 >=10%")
    if block.get("manchester_brca2_over_10pct") is True:
        flags.append("BRCA2 >=10%")
    if block.get("manchester_combined_over_20pct") is True:
        flags.append("combined >=20%")
    return ModelSummary(
        model=model,
        headline=f"BRCA1 score {brca1}, BRCA2 score {brca2}, combined {combined}",
        detail="Manchester scoring (Evans et al. 2004)",
        threshold_label=", ".join(flags),
        triggers=_string_tuple(block.get("manchester_contributions")),
    )


def _summarise_nice(model: str, block: dict[str, Any]) -> ModelSummary:
    category = block.get("nice_category")
    refer = block.get("nice_refer_genetics")
    headline = _nice_headline(category)
    detail = "refer for genetics assessment" if refer is True else "no genetics referral indicated"
    return ModelSummary(
        model=model,
        headline=headline,
        detail=detail,
        threshold_label="",
        triggers=_string_tuple(block.get("nice_triggers")),
    )


def _summarise_tyrer_cuzick(model: str, block: dict[str, Any]) -> ModelSummary:
    ten_year = _optional_percent(block.get("tc_ten_year_risk"))
    lifetime = _optional_percent(block.get("tc_lifetime_risk"))
    age = block.get("tc_proband_age")
    detail = f"proband age {age}" if isinstance(age, int) and age > 0 else ""
    return ModelSummary(
        model=model,
        headline=f"10-year {ten_year} / lifetime {lifetime}",
        detail=detail,
        threshold_label="",
        triggers=(),
    )


_SUMMARISERS = {
    "CLAUS": _summarise_claus,
    "COUCH": _summarise_couch,
    "FRANK": _summarise_frank,
    "MANCHESTER": _summarise_manchester,
    "NICE": _summarise_nice,
    "TYRER_CUZICK": _summarise_tyrer_cuzick,
}


_NICE_HEADLINES = {
    "near_population": "Near-population risk (NICE <17% lifetime)",
    "moderate": "Moderate risk (NICE 17-30% lifetime)",
    "high": "High risk (NICE >=30% lifetime)",
}


def _nice_headline(category: Any) -> str:
    if isinstance(category, str) and category in _NICE_HEADLINES:
        return _NICE_HEADLINES[category]
    return "NICE category unavailable"


def _optional_percent(value: Any) -> str:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f"{100 * value:.1f}%"
    return "-"


def _optional_int(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return "-"


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))
