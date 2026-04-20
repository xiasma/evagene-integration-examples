"""End-to-end composition tests with an in-memory fake Evagene API.

The fake replaces both the network client and the rebuild orchestration,
so we exercise the real :class:`_RebuildOrchestrator` against recorded
calls.  The intake-form demo is the reference sequence; we verify the
sequence here (create_pedigree, create_individual, add_individual,
designate_as_proband, add_relative, add_relative, ...)."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from research_anonymiser.evagene_client import (
    AddRelativeArgs,
    CreateIndividualArgs,
    EvageneClient,
    _RebuildOrchestrator,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@dataclass
class _Call:
    op: str
    payload: Any


@dataclass
class _RecordingClient:
    calls: list[_Call] = field(default_factory=list)
    _counter: int = 0

    def _issue_id(self) -> str:
        self._counter += 1
        return f"id-{self._counter:04d}"

    def create_pedigree(self, display_name: str) -> str:
        new_id = self._issue_id()
        self.calls.append(
            _Call("create_pedigree", {"display_name": display_name, "returned": new_id})
        )
        return new_id

    def create_individual(self, args: CreateIndividualArgs) -> str:
        new_id = self._issue_id()
        self.calls.append(_Call("create_individual", {"args": args, "returned": new_id}))
        return new_id

    def add_individual_to_pedigree(self, pedigree_id: str, individual_id: str) -> None:
        self.calls.append(
            _Call(
                "add_individual_to_pedigree",
                {"pedigree_id": pedigree_id, "individual_id": individual_id},
            )
        )

    def designate_as_proband(self, individual_id: str) -> None:
        self.calls.append(_Call("designate_as_proband", {"individual_id": individual_id}))

    def add_relative(self, args: AddRelativeArgs) -> str:
        new_id = self._issue_id()
        self.calls.append(_Call("add_relative", {"args": args, "returned": new_id}))
        return new_id


def _ops(client: _RecordingClient) -> list[str]:
    return [call.op for call in client.calls]


def _anonymised_fixture() -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(
        (FIXTURES / "expected-anonymised.json").read_text("utf-8")
    )
    return parsed


def test_rebuild_sequence_mirrors_the_intake_form_demo() -> None:
    anonymised = _anonymised_fixture()
    client = _RecordingClient()

    new_pedigree_id = _RebuildOrchestrator(client, anonymised).run()  # type: ignore[arg-type]

    ops = _ops(client)
    assert ops[:4] == [
        "create_pedigree",
        "create_individual",
        "add_individual_to_pedigree",
        "designate_as_proband",
    ]
    assert all(op == "add_relative" for op in ops[4:])
    assert new_pedigree_id.startswith("id-")


def test_proband_is_created_with_anonymised_display_name_not_source_name() -> None:
    anonymised = _anonymised_fixture()
    client = _RecordingClient()

    _RebuildOrchestrator(client, anonymised).run()  # type: ignore[arg-type]

    proband_call = next(call for call in client.calls if call.op == "create_individual")
    args: CreateIndividualArgs = proband_call.payload["args"]
    assert args.display_name == "III-1"
    assert args.biological_sex == "female"


def test_relatives_are_added_with_sex_derived_relative_types() -> None:
    anonymised = _anonymised_fixture()
    client = _RecordingClient()

    _RebuildOrchestrator(client, anonymised).run()  # type: ignore[arg-type]

    relative_types = [
        call.payload["args"].relative_type
        for call in client.calls
        if call.op == "add_relative"
    ]
    # Proband first sees her parents (mother + father), then her sibling (brother).
    assert "mother" in relative_types
    assert "father" in relative_types
    assert "brother" in relative_types


def test_app_run_prints_new_pedigree_id_on_as_new_pedigree_path() -> None:
    from research_anonymiser.app import EXIT_OK, _anonymise
    from research_anonymiser.config import AgePrecision, Config

    config = Config(
        base_url="https://evagene.example",
        api_key="evg_test",
        pedigree_id="00000000-0000-0000-0000-000000000000",
        output_path=None,
        as_new_pedigree=True,
        age_precision=AgePrecision.YEAR,
        keep_sex=True,
    )

    source = json.loads((FIXTURES / "source-pedigree.json").read_text("utf-8"))

    @dataclass
    class _FakeApi:
        pedigree: dict[str, Any]
        last_rebuild_arg: dict[str, Any] | None = None

        def get_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]:
            del pedigree_id
            return self.pedigree

        def rebuild_pedigree(self, anonymised: dict[str, Any]) -> str:
            self.last_rebuild_arg = anonymised
            return "new-pedigree-id"

    client = _FakeApi(source)
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = _anonymise(config, client, stdout, stderr)

    assert exit_code == EXIT_OK
    assert stdout.getvalue().strip() == "new-pedigree-id"
    assert client.last_rebuild_arg is not None


def test_app_run_writes_file_when_output_given(tmp_path: Path) -> None:
    from research_anonymiser.app import EXIT_OK, _anonymise
    from research_anonymiser.config import AgePrecision, Config

    output_path = tmp_path / "anon.json"
    config = Config(
        base_url="https://evagene.example",
        api_key="evg_test",
        pedigree_id="00000000-0000-0000-0000-000000000000",
        output_path=str(output_path),
        as_new_pedigree=False,
        age_precision=AgePrecision.YEAR,
        keep_sex=True,
    )
    source = json.loads((FIXTURES / "source-pedigree.json").read_text("utf-8"))

    @dataclass
    class _ReadOnlyFake:
        pedigree: dict[str, Any]

        def get_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]:
            del pedigree_id
            return self.pedigree

        def rebuild_pedigree(self, anonymised: dict[str, Any]) -> str:
            raise AssertionError("--as-new-pedigree not requested")

    exit_code = _anonymise(
        config, _ReadOnlyFake(source), io.StringIO(), io.StringIO()
    )

    assert exit_code == EXIT_OK
    assert output_path.exists()
    document = json.loads(output_path.read_text("utf-8"))
    assert document["display_name"] == "Anonymised pedigree"
    assert "k_anonymity" in document


def test_evagene_client_is_the_concrete_api() -> None:
    """Keeps the real client in the type graph (mypy strict catches drift)."""
    assert hasattr(EvageneClient, "get_pedigree_detail")
    assert hasattr(EvageneClient, "rebuild_pedigree")
