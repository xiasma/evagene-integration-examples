import io
from typing import Any

import pytest

from couple_carrier_risk.config import Config
from couple_carrier_risk.evagene_client import EvageneClient
from couple_carrier_risk.orchestrator import (
    SCRATCH_PEDIGREE_NAME,
    AncestryNotFoundError,
    run_couple_screening,
)
from tests.fixtures_loader import fixture_path


def _config(ancestry_a: str = "auto", ancestry_b: str = "auto", cleanup: bool = True) -> Config:
    return Config(
        base_url="https://evagene.example",
        api_key="evg_test",
        partner_a_file=str(fixture_path("partner-a-23andme.txt")),
        partner_b_file=str(fixture_path("partner-b-23andme.txt")),
        ancestry_a=ancestry_a,
        ancestry_b=ancestry_b,
        output_format="table",
        cleanup=cleanup,
    )


class _FakeClient:
    """Captures every call the orchestrator makes and returns canned responses."""

    def __init__(self) -> None:
        self.created_pedigrees: list[str] = []
        self.created_individuals: list[tuple[str, str]] = []  # (display_name, sex)
        self.pedigree_memberships: list[tuple[str, str]] = []
        self.imported_tsvs: list[tuple[str, str]] = []
        self.deleted_pedigrees: list[str] = []
        self.deleted_individuals: list[str] = []
        self.recorded_ancestries: list[tuple[str, str]] = []
        self.ancestry_lookup: dict[str, str | None] = {}
        self._next_id = 0

    def _fresh_id(self, prefix: str) -> str:
        self._next_id += 1
        return f"{prefix}-{self._next_id}"

    def create_pedigree(self, display_name: str) -> str:
        identifier = self._fresh_id("ped")
        self.created_pedigrees.append(display_name)
        return identifier

    def delete_pedigree(self, pedigree_id: str) -> None:
        self.deleted_pedigrees.append(pedigree_id)

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None:
        self.pedigree_memberships.append((pedigree_id, individual_id))

    def create_individual(self, *, display_name: str, biological_sex: Any) -> Any:
        identifier = self._fresh_id("ind")
        self.created_individuals.append((display_name, biological_sex.value))
        from couple_carrier_risk.evagene_client import Individual
        return Individual(id=identifier, display_name=display_name)

    def delete_individual(self, individual_id: str) -> None:
        self.deleted_individuals.append(individual_id)

    def import_23andme_raw(self, *, pedigree_id: str, individual_id: str, tsv: str) -> None:
        self.imported_tsvs.append((individual_id, tsv[:20]))

    def find_ancestry_id_by_population_key(self, population_key: str) -> str | None:
        return self.ancestry_lookup.get(population_key)

    def add_ancestry_to_individual(
        self, *, individual_id: str, ancestry_id: str, proportion: float = 1.0,
    ) -> None:
        self.recorded_ancestries.append((individual_id, ancestry_id))

    def get_population_risks(self, individual_id: str) -> dict[str, Any]:
        return {
            "individual_id": individual_id,
            "risks": [
                {
                    "disease_id": "d1",
                    "disease_name": "Sickle cell anaemia",
                    "inheritance_pattern": "autosomal_recessive",
                    "carrier_frequency": 0.05,
                    "couple_offspring_risk": 0.000625,
                },
            ],
        }


def test_end_to_end_happy_path_creates_scratch_and_renders_table() -> None:
    client = _FakeClient()
    sink = io.StringIO()

    run_couple_screening(_config(), client, sink)  # type: ignore[arg-type]

    output = sink.getvalue()
    assert "Sickle cell anaemia" in output
    assert client.created_pedigrees == [SCRATCH_PEDIGREE_NAME]
    assert [entry[0] for entry in client.created_individuals] == ["Partner A", "Partner B"]
    assert len(client.imported_tsvs) == 2


def test_cleanup_deletes_pedigree_and_individuals_on_success() -> None:
    client = _FakeClient()

    run_couple_screening(_config(cleanup=True), client, io.StringIO())  # type: ignore[arg-type]

    assert len(client.deleted_individuals) == 2
    assert len(client.deleted_pedigrees) == 1


def test_no_cleanup_flag_leaves_scratch_in_place() -> None:
    client = _FakeClient()

    run_couple_screening(_config(cleanup=False), client, io.StringIO())  # type: ignore[arg-type]

    assert client.deleted_pedigrees == []
    assert client.deleted_individuals == []


def test_cleanup_runs_even_when_risk_fetch_fails() -> None:
    class _FlakyClient(_FakeClient):
        def get_population_risks(self, individual_id: str) -> dict[str, Any]:
            raise RuntimeError("network broke mid-run")

    client = _FlakyClient()

    with pytest.raises(RuntimeError, match="network broke"):
        run_couple_screening(_config(cleanup=True), client, io.StringIO())  # type: ignore[arg-type]

    assert client.deleted_pedigrees, "pedigree must still be deleted on failure"


def test_explicit_ancestry_is_looked_up_and_attached() -> None:
    client = _FakeClient()
    client.ancestry_lookup = {"mediterranean": "anc-uuid"}

    run_couple_screening(
        _config(ancestry_a="mediterranean", ancestry_b="mediterranean"),
        client,  # type: ignore[arg-type]
        io.StringIO(),
    )

    assert [entry[1] for entry in client.recorded_ancestries] == ["anc-uuid", "anc-uuid"]


def test_unknown_ancestry_key_raises_ancestry_not_found() -> None:
    client = _FakeClient()
    client.ancestry_lookup = {}

    with pytest.raises(AncestryNotFoundError):
        run_couple_screening(
            _config(ancestry_a="klingon"),
            client,  # type: ignore[arg-type]
            io.StringIO(),
        )


def test_fake_client_implements_evagene_client_surface() -> None:
    """Smoke-check: every method used by the orchestrator exists on EvageneClient."""
    required = {
        "create_pedigree",
        "delete_pedigree",
        "add_individual_to_pedigree",
        "create_individual",
        "delete_individual",
        "import_23andme_raw",
        "find_ancestry_id_by_population_key",
        "add_ancestry_to_individual",
        "get_population_risks",
    }
    for name in required:
        assert hasattr(EvageneClient, name), f"EvageneClient missing {name!r}"
