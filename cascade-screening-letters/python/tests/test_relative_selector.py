import json
from pathlib import Path

from cascade_letters.evagene_client import RegisterData, RegisterRow
from cascade_letters.relative_selector import select_at_risk_relatives

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _row(
    ind_id: str = "b0000000-0000-0000-0000-000000000001",
    display_name: str = "Someone",
    relationship: str = "Sister",
) -> RegisterRow:
    return RegisterRow(
        individual_id=ind_id,
        display_name=display_name,
        relationship_to_proband=relationship,
    )


def _register(*rows: RegisterRow, proband_id: str | None = None) -> RegisterData:
    return RegisterData(proband_id=proband_id, rows=rows)


def test_selects_first_and_second_degree_relatives_from_fixture() -> None:
    raw = json.loads((FIXTURES / "sample-register.json").read_text(encoding="utf-8"))
    register = RegisterData(
        proband_id=raw["proband_id"],
        rows=tuple(
            RegisterRow(
                individual_id=r["individual_id"],
                display_name=r["display_name"],
                relationship_to_proband=r["relationship_to_proband"],
            )
            for r in raw["rows"]
        ),
    )

    targets = select_at_risk_relatives(register)
    names = [t.display_name for t in targets]

    assert "Helen Ward" not in names  # proband excluded
    assert "Annabel Hargreaves" not in names  # First cousin is third-degree, excluded
    assert "" not in names  # half-sister without a display name is skipped
    assert names == [
        "Margaret Ward",
        "David Ward",
        "Sarah Ward",
        "Thomas Ward",
        "Joan Pembroke",
        "Elizabeth Pembroke",
    ]


def test_skips_proband() -> None:
    proband_id = "b0000000-0000-0000-0000-000000000042"
    register = _register(
        _row(ind_id=proband_id, display_name="Proband Name", relationship="Proband"),
        proband_id=proband_id,
    )

    assert select_at_risk_relatives(register) == []


def test_skips_row_with_blank_display_name() -> None:
    register = _register(_row(display_name="   ", relationship="Sister"))

    assert select_at_risk_relatives(register) == []


def test_accepts_side_suffixed_second_degree_labels() -> None:
    register = _register(
        _row(display_name="Maternal Grandma", relationship="Grandmother (maternal)"),
        _row(display_name="Paternal Uncle", relationship="Uncle (paternal)"),
    )

    assert [t.display_name for t in select_at_risk_relatives(register)] == [
        "Maternal Grandma",
        "Paternal Uncle",
    ]


def test_rejects_third_degree_and_more_distant() -> None:
    register = _register(
        _row(display_name="Great-grandma", relationship="Great-Grandmother (maternal)"),
        _row(display_name="First cousin", relationship="First cousin (paternal)"),
        _row(display_name="Great-uncle", relationship="Great-uncle (maternal)"),
    )

    assert select_at_risk_relatives(register) == []


def test_rejects_unlabelled_rows() -> None:
    register = _register(_row(display_name="Mystery", relationship=""))

    assert select_at_risk_relatives(register) == []


def test_accepts_all_first_degree_base_labels() -> None:
    labels = ("Father", "Mother", "Parent", "Brother", "Sister", "Sibling", "Son", "Daughter")
    register = _register(
        *(
            _row(
                ind_id=f"b0000000-0000-0000-0000-0000000000{idx:02d}",
                display_name=f"Person {label}",
                relationship=label,
            )
            for idx, label in enumerate(labels, start=10)
        )
    )

    assert len(select_at_risk_relatives(register)) == len(labels)
