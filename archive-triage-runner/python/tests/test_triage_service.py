from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from archive_triage.evagene_client import EvageneApiError
from archive_triage.gedcom_scanner import GedcomFile
from archive_triage.triage_service import TriageOptions, TriageService


@dataclass
class _FakeClient:
    created_ids: list[str] = field(default_factory=lambda: ["pedigree-1"])
    imports_raise: Exception | None = None
    has_proband_result: bool = True
    nice_payload: dict[str, Any] = field(
        default_factory=lambda: {
            "counselee_name": "Jane Doe",
            "cancer_risk": {
                "nice_category": "high",
                "nice_refer_genetics": True,
                "nice_triggers": ["trigger A", "trigger B"],
            },
        }
    )
    create_raises: Exception | None = None
    calculate_raises: Exception | None = None

    created_calls: list[str] = field(default_factory=list)
    imported_calls: list[tuple[str, str]] = field(default_factory=list)
    calculated_ids: list[str] = field(default_factory=list)

    def create_pedigree(self, display_name: str) -> str:
        if self.create_raises is not None:
            raise self.create_raises
        self.created_calls.append(display_name)
        return self.created_ids.pop(0)

    def import_gedcom(self, pedigree_id: str, gedcom_text: str) -> None:
        if self.imports_raise is not None:
            raise self.imports_raise
        self.imported_calls.append((pedigree_id, gedcom_text))

    def has_proband(self, pedigree_id: str) -> bool:
        return self.has_proband_result

    def calculate_nice(self, pedigree_id: str) -> dict[str, Any]:
        if self.calculate_raises is not None:
            raise self.calculate_raises
        self.calculated_ids.append(pedigree_id)
        return self.nice_payload

    def delete_pedigree(self, pedigree_id: str) -> None:  # pragma: no cover - unused here
        pass


def _service(client: _FakeClient) -> TriageService:
    return TriageService(client, TriageOptions(concurrency=1))


def _file(name: str) -> GedcomFile:
    return GedcomFile(path=Path(name), content=f"{name}-content")


def test_happy_path_emits_one_row_per_file_with_trigger_count() -> None:
    client = _FakeClient(created_ids=["pedigree-1"])

    rows = list(_service(client).triage([_file("family.ged")]))

    assert len(rows) == 1
    assert rows[0].pedigree_id == "pedigree-1"
    assert rows[0].proband_name == "Jane Doe"
    assert rows[0].category == "high"
    assert rows[0].refer_for_genetics is True
    assert rows[0].triggers_matched_count == 2
    assert rows[0].error == ""


def test_display_name_comes_from_filename_stem() -> None:
    client = _FakeClient(created_ids=["pedigree-1"])

    list(_service(client).triage([_file("smith-family.ged")]))

    assert client.created_calls == ["smith-family"]


def test_gedcom_text_passed_through_to_import() -> None:
    client = _FakeClient(created_ids=["pedigree-1"])

    list(_service(client).triage([_file("family.ged")]))

    assert client.imported_calls == [("pedigree-1", "family.ged-content")]


def test_missing_proband_produces_failure_row_without_running_risk() -> None:
    client = _FakeClient(created_ids=["pedigree-1"], has_proband_result=False)

    rows = list(_service(client).triage([_file("family.ged")]))

    assert rows[0].error.startswith("no proband")
    assert rows[0].category == ""
    assert rows[0].triggers_matched_count == 0
    assert client.calculated_ids == []


def test_create_pedigree_failure_produces_row_with_empty_pedigree_id() -> None:
    client = _FakeClient(create_raises=EvageneApiError("HTTP 503"))

    rows = list(_service(client).triage([_file("family.ged")]))

    assert rows[0].pedigree_id == ""
    assert rows[0].proband_name == "family"
    assert "create_pedigree failed" in rows[0].error


def test_risk_calculation_failure_preserves_pedigree_id_in_row() -> None:
    client = _FakeClient(
        created_ids=["pedigree-1"],
        calculate_raises=EvageneApiError("HTTP 500"),
    )

    rows = list(_service(client).triage([_file("family.ged")]))

    assert rows[0].pedigree_id == "pedigree-1"
    assert "calculate_nice failed" in rows[0].error


def test_schema_drift_in_nice_payload_becomes_error_row() -> None:
    client = _FakeClient(
        created_ids=["pedigree-1"],
        nice_payload={"counselee_name": "Jane", "cancer_risk": {"nice_category": ""}},
    )

    rows = list(_service(client).triage([_file("family.ged")]))

    assert "schema" in rows[0].error


def test_every_file_gets_a_row_even_when_some_fail() -> None:
    client = _FakeClient(created_ids=["pedigree-1", "pedigree-2"])

    rows = list(
        _service(client).triage([_file("a.ged"), _file("b.ged")])
    )

    assert len(rows) == 2
