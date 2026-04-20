"""Pure transform: two population-risk payloads -> a per-disease couple table.

The Evagene API already returns ``couple_offspring_risk`` per row, but
that figure assumes a same-ancestry, untested partner. When *both*
partners' carrier frequencies are known (the happy path in this demo),
we can refine the estimate to a genuinely cross-partner value:

- AR:  cf_a * cf_b / 4  (each partner independently transmits with P = 1/2
                         given they are a carrier, so the joint per-pregnancy
                         affected-child probability is cf_a * cf_b * 1/4).
- XLR: cf_female / 4    (mother carrier * 1/2 transmission * 1/2 son; the
                         father's carrier state is irrelevant).

The refinement runs only when the API supplied both carrier frequencies
on the disease; single-partner rows carry through untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .genome_file import BiologicalSex

INHERITANCE_AR = "autosomal_recessive"
INHERITANCE_XLR = "x_linked_recessive"


class ResponseSchemaError(ValueError):
    """Raised when a population-risks payload does not match the documented schema."""


@dataclass(frozen=True)
class CoupleRow:
    disease_name: str
    inheritance_pattern: str
    carrier_frequency_a: float | None
    carrier_frequency_b: float | None
    api_couple_offspring_risk_a: float | None
    api_couple_offspring_risk_b: float | None
    cross_partner_offspring_risk: float | None


@dataclass(frozen=True)
class PartnerRisks:
    biological_sex: BiologicalSex
    risks: dict[str, dict[str, Any]]  # keyed by disease_name


def build_couple_rows(
    partner_a: PartnerRisks,
    partner_b: PartnerRisks,
) -> tuple[CoupleRow, ...]:
    """Combine two partners' population-risks into one row per disease.

    Row order follows partner A's disease order, with any B-only diseases
    appended in the order they appear in B's response.
    """
    disease_names = _union_preserving_order(partner_a.risks, partner_b.risks)
    return tuple(
        _build_row(partner_a, partner_b, disease_name) for disease_name in disease_names
    )


def parse_population_risks(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract the ``risks`` list from a population-risks response into a dict."""
    risks = payload.get("risks")
    if not isinstance(risks, list):
        raise ResponseSchemaError("population-risks response lacks a 'risks' list")

    indexed: dict[str, dict[str, Any]] = {}
    for entry in risks:
        if not isinstance(entry, dict):
            raise ResponseSchemaError(
                f"population-risks 'risks[]' entry is not an object: {entry!r}",
            )
        disease_name = entry.get("disease_name")
        if not isinstance(disease_name, str) or not disease_name:
            raise ResponseSchemaError(
                "population-risks row lacks a string 'disease_name'",
            )
        indexed[disease_name] = entry
    return indexed


def _build_row(
    partner_a: PartnerRisks,
    partner_b: PartnerRisks,
    disease_name: str,
) -> CoupleRow:
    row_a = partner_a.risks.get(disease_name)
    row_b = partner_b.risks.get(disease_name)
    inheritance = _inheritance_of(row_a, row_b)

    cf_a = _number_or_none(row_a, "carrier_frequency") if row_a else None
    cf_b = _number_or_none(row_b, "carrier_frequency") if row_b else None

    return CoupleRow(
        disease_name=disease_name,
        inheritance_pattern=inheritance,
        carrier_frequency_a=cf_a,
        carrier_frequency_b=cf_b,
        api_couple_offspring_risk_a=(
            _number_or_none(row_a, "couple_offspring_risk") if row_a else None
        ),
        api_couple_offspring_risk_b=(
            _number_or_none(row_b, "couple_offspring_risk") if row_b else None
        ),
        cross_partner_offspring_risk=_cross_partner_risk(
            inheritance,
            cf_a=cf_a,
            cf_b=cf_b,
            biological_sex_a=partner_a.biological_sex,
            biological_sex_b=partner_b.biological_sex,
        ),
    )


def _cross_partner_risk(
    inheritance: str,
    *,
    cf_a: float | None,
    cf_b: float | None,
    biological_sex_a: BiologicalSex,
    biological_sex_b: BiologicalSex,
) -> float | None:
    if inheritance == INHERITANCE_AR:
        if cf_a is None or cf_b is None:
            return None
        return cf_a * cf_b / 4.0

    if inheritance == INHERITANCE_XLR:
        cf_female = _female_carrier_frequency(
            cf_a=cf_a, cf_b=cf_b,
            biological_sex_a=biological_sex_a, biological_sex_b=biological_sex_b,
        )
        if cf_female is None:
            return None
        return cf_female / 4.0

    return None


def _female_carrier_frequency(
    *,
    cf_a: float | None,
    cf_b: float | None,
    biological_sex_a: BiologicalSex,
    biological_sex_b: BiologicalSex,
) -> float | None:
    if biological_sex_a is BiologicalSex.FEMALE:
        return cf_a
    if biological_sex_b is BiologicalSex.FEMALE:
        return cf_b
    return None


def _inheritance_of(
    row_a: dict[str, Any] | None,
    row_b: dict[str, Any] | None,
) -> str:
    for row in (row_a, row_b):
        if row is None:
            continue
        pattern = row.get("inheritance_pattern")
        if isinstance(pattern, str) and pattern:
            return pattern
    raise ResponseSchemaError(
        "population-risks row lacks a string 'inheritance_pattern'",
    )


def _number_or_none(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ResponseSchemaError(f"population-risks field {key!r} is not a number")
    return float(value)


def _union_preserving_order(
    first: dict[str, dict[str, Any]],
    second: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    seen = list(first.keys())
    for name in second:
        if name not in first:
            seen.append(name)
    return tuple(seen)
