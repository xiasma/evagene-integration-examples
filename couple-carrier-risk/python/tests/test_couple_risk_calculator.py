from typing import Any

import pytest

from couple_carrier_risk.couple_risk_calculator import (
    INHERITANCE_AR,
    INHERITANCE_XLR,
    PartnerRisks,
    ResponseSchemaError,
    build_couple_rows,
    parse_population_risks,
)
from couple_carrier_risk.genome_file import BiologicalSex
from tests.fixtures_loader import load_json_fixture


def _risks(*entries: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["disease_name"]: entry for entry in entries}


def _ar(name: str, cf: float | None, *, couple: float | None = None) -> dict[str, Any]:
    return {
        "disease_name": name,
        "inheritance_pattern": INHERITANCE_AR,
        "carrier_frequency": cf,
        "couple_offspring_risk": couple,
    }


def _xlr(name: str, cf: float | None, *, couple: float | None = None) -> dict[str, Any]:
    return {
        "disease_name": name,
        "inheritance_pattern": INHERITANCE_XLR,
        "carrier_frequency": cf,
        "couple_offspring_risk": couple,
    }


def test_parse_population_risks_indexes_by_disease_name() -> None:
    indexed = parse_population_risks(load_json_fixture("sample-population-risks"))

    assert set(indexed) == {
        "Sickle cell anaemia",
        "Cystic fibrosis",
        "Duchenne muscular dystrophy",
    }
    assert indexed["Sickle cell anaemia"]["inheritance_pattern"] == INHERITANCE_AR


def test_parse_population_risks_requires_risks_list() -> None:
    with pytest.raises(ResponseSchemaError):
        parse_population_risks({})


def test_ar_cross_partner_risk_is_cf_a_times_cf_b_over_four() -> None:
    partner_a = PartnerRisks(
        biological_sex=BiologicalSex.MALE,
        risks=_risks(_ar("Sickle cell", 0.08, couple=0.0016)),
    )
    partner_b = PartnerRisks(
        biological_sex=BiologicalSex.FEMALE,
        risks=_risks(_ar("Sickle cell", 0.05, couple=0.000625)),
    )

    rows = build_couple_rows(partner_a, partner_b)

    assert len(rows) == 1
    row = rows[0]
    assert row.carrier_frequency_a == 0.08
    assert row.carrier_frequency_b == 0.05
    assert row.cross_partner_offspring_risk == pytest.approx(0.08 * 0.05 / 4)


def test_ar_with_one_missing_cf_yields_no_cross_partner_risk() -> None:
    partner_a = PartnerRisks(BiologicalSex.MALE, _risks(_ar("X", 0.05, couple=0.0006)))
    partner_b = PartnerRisks(BiologicalSex.FEMALE, {})

    rows = build_couple_rows(partner_a, partner_b)

    assert rows[0].cross_partner_offspring_risk is None
    assert rows[0].carrier_frequency_b is None


def test_xlr_uses_only_the_female_partners_carrier_frequency() -> None:
    partner_a = PartnerRisks(BiologicalSex.MALE, _risks(_xlr("DMD", 0.0, couple=0.0)))
    partner_b = PartnerRisks(
        biological_sex=BiologicalSex.FEMALE,
        risks=_risks(_xlr("DMD", 0.002, couple=0.0005)),
    )

    rows = build_couple_rows(partner_a, partner_b)

    assert rows[0].cross_partner_offspring_risk == pytest.approx(0.002 / 4)


def test_xlr_with_no_female_partner_yields_no_cross_partner_risk() -> None:
    partner_a = PartnerRisks(BiologicalSex.MALE, _risks(_xlr("DMD", 0.002)))
    partner_b = PartnerRisks(BiologicalSex.MALE, _risks(_xlr("DMD", 0.002)))

    rows = build_couple_rows(partner_a, partner_b)

    assert rows[0].cross_partner_offspring_risk is None


def test_rows_union_preserves_partner_a_order_then_b_only_entries() -> None:
    partner_a = PartnerRisks(
        biological_sex=BiologicalSex.MALE,
        risks=_risks(_ar("A-only", 0.01), _ar("Shared", 0.02)),
    )
    partner_b = PartnerRisks(
        biological_sex=BiologicalSex.FEMALE,
        risks=_risks(_ar("Shared", 0.03), _ar("B-only", 0.04)),
    )

    rows = build_couple_rows(partner_a, partner_b)

    assert [row.disease_name for row in rows] == ["A-only", "Shared", "B-only"]


def test_non_numeric_carrier_frequency_raises_schema_error() -> None:
    partner_a = PartnerRisks(
        biological_sex=BiologicalSex.MALE,
        risks=_risks({
            "disease_name": "Bad",
            "inheritance_pattern": INHERITANCE_AR,
            "carrier_frequency": "oops",
        }),
    )
    partner_b = PartnerRisks(BiologicalSex.FEMALE, {})

    with pytest.raises(ResponseSchemaError):
        build_couple_rows(partner_a, partner_b)
