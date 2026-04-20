from dataclasses import dataclass, field
from typing import Any

from pedigree_ocr.evagene_client import (
    AddRelativeArgs,
    CreateIndividualArgs,
)
from pedigree_ocr.evagene_writer import EvageneWriter
from pedigree_ocr.extracted_family import (
    BiologicalSex,
    ExtractedFamily,
    ProbandEntry,
    RelativeEntry,
    SiblingEntry,
    SiblingRelation,
)


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


def _family(**overrides: Any) -> ExtractedFamily:
    defaults: dict[str, Any] = {
        "proband": ProbandEntry(display_name="Emma", biological_sex=BiologicalSex.FEMALE),
        "siblings": (),
    }
    defaults.update(overrides)
    return ExtractedFamily(**defaults)


def _ops(client: _RecordingClient) -> list[str]:
    return [call.op for call in client.calls]


def test_proband_only_family_performs_setup_then_stops() -> None:
    client = _RecordingClient()

    result = EvageneWriter(client).write(_family())

    assert _ops(client) == [
        "create_pedigree",
        "create_individual",
        "add_individual_to_pedigree",
        "designate_as_proband",
    ]
    assert result.relatives_added == 0


def test_parents_added_before_their_grandparents() -> None:
    client = _RecordingClient()

    EvageneWriter(client).write(
        _family(
            mother=RelativeEntry(display_name="Grace"),
            father=RelativeEntry(display_name="Henry"),
            maternal_grandmother=RelativeEntry(display_name="Edith"),
            paternal_grandfather=RelativeEntry(display_name="Arthur"),
        )
    )

    relatives = [
        (call.payload["args"].relative_type, call.payload["args"].display_name)
        for call in client.calls
        if call.op == "add_relative"
    ]
    assert relatives == [
        ("mother", "Grace"),
        ("father", "Henry"),
        ("mother", "Edith"),
        ("father", "Arthur"),
    ]


def test_grandparent_with_no_parent_is_skipped() -> None:
    client = _RecordingClient()

    EvageneWriter(client).write(_family(maternal_grandmother=RelativeEntry(display_name="Edith")))

    assert not any(call.op == "add_relative" for call in client.calls)


def test_sibling_sex_is_derived_from_relation() -> None:
    client = _RecordingClient()

    EvageneWriter(client).write(
        _family(
            siblings=(
                SiblingEntry(display_name="Alice", relation=SiblingRelation.SISTER),
                SiblingEntry(display_name="Ben", relation=SiblingRelation.HALF_BROTHER),
            )
        )
    )

    sibling_calls = [call for call in client.calls if call.op == "add_relative"]
    alice_args = sibling_calls[0].payload["args"]
    ben_args = sibling_calls[1].payload["args"]
    assert alice_args.biological_sex is BiologicalSex.FEMALE
    assert alice_args.relative_type == "sister"
    assert ben_args.biological_sex is BiologicalSex.MALE
    assert ben_args.relative_type == "half_brother"
