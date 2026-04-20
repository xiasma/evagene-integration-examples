from dataclasses import dataclass, field

import pytest

from cascade_letters.cascade_service import (
    CascadeRequest,
    CascadeService,
    NoAtRiskRelativesError,
)
from cascade_letters.evagene_client import (
    CreateTemplateArgs,
    RegisterData,
    RegisterRow,
    Template,
)
from cascade_letters.letter_writer import LetterFile

_PROBAND_ID = "a0000000-0000-0000-0000-000000000001"
_SISTER_ID = "a0000000-0000-0000-0000-000000000002"
_PEDIGREE_ID = "f0000000-0000-0000-0000-000000000000"


def _brca_register() -> RegisterData:
    return RegisterData(
        proband_id=_PROBAND_ID,
        rows=(
            RegisterRow(
                individual_id=_PROBAND_ID,
                display_name="Helen Ward",
                relationship_to_proband="Proband",
            ),
            RegisterRow(
                individual_id=_SISTER_ID,
                display_name="Sarah Ward",
                relationship_to_proband="Sister",
            ),
        ),
    )


@dataclass
class _FakeClient:
    register: RegisterData
    templates: list[Template] = field(default_factory=list)
    rendered_body: str = "Template body.\n"
    run_calls: list[tuple[str, str]] = field(default_factory=list)

    def fetch_register(self, pedigree_id: str) -> RegisterData:
        assert pedigree_id
        return self.register

    def list_templates(self) -> list[Template]:
        return list(self.templates)

    def create_template(self, args: CreateTemplateArgs) -> Template:
        created = Template(id="auto-created", name=args.name)
        self.templates.append(created)
        return created

    def run_template(self, template_id: str, pedigree_id: str) -> str:
        self.run_calls.append((template_id, pedigree_id))
        return self.rendered_body


@dataclass
class _RecordingSink:
    letters: list[LetterFile] = field(default_factory=list)

    def write(self, letter: LetterFile) -> str:
        self.letters.append(letter)
        return f"memory://{letter.filename}"


def _service(client: _FakeClient, sink: _RecordingSink) -> CascadeService:
    return CascadeService(client=client, sink=sink)


def test_dry_run_lists_targets_without_calling_run_template() -> None:
    client = _FakeClient(register=_brca_register())
    sink = _RecordingSink()

    result = _service(client, sink).generate_letters(
        CascadeRequest(pedigree_id=_PEDIGREE_ID, template_override=None, dry_run=True)
    )

    assert [t.display_name for t in result.targets] == ["Sarah Ward"]
    assert result.written_paths == ()
    assert client.run_calls == []
    assert sink.letters == []


def test_full_run_writes_one_letter_per_target() -> None:
    client = _FakeClient(register=_brca_register())
    sink = _RecordingSink()

    result = _service(client, sink).generate_letters(
        CascadeRequest(
            pedigree_id=_PEDIGREE_ID, template_override="override-id", dry_run=False
        )
    )

    assert len(sink.letters) == 1
    assert sink.letters[0].filename == "01-sarah-ward.md"
    assert "Sarah Ward" in sink.letters[0].content
    assert "Template body." in sink.letters[0].content
    assert result.written_paths == ("memory://01-sarah-ward.md",)
    assert client.run_calls == [("override-id", _PEDIGREE_ID)]


def test_run_without_override_uses_or_creates_template() -> None:
    client = _FakeClient(register=_brca_register())
    sink = _RecordingSink()

    _service(client, sink).generate_letters(
        CascadeRequest(pedigree_id=_PEDIGREE_ID, template_override=None, dry_run=False)
    )

    assert client.run_calls[0][0] == "auto-created"


def test_register_with_no_proband_raises() -> None:
    register = RegisterData(proband_id=None, rows=())
    client = _FakeClient(register=register)
    sink = _RecordingSink()

    with pytest.raises(NoAtRiskRelativesError, match="no designated proband"):
        _service(client, sink).generate_letters(
            CascadeRequest(pedigree_id=_PEDIGREE_ID, template_override=None, dry_run=False)
        )


def test_register_without_relatives_raises() -> None:
    register = RegisterData(
        proband_id=_PROBAND_ID,
        rows=(
            RegisterRow(
                individual_id=_PROBAND_ID,
                display_name="Helen Ward",
                relationship_to_proband="Proband",
            ),
        ),
    )
    client = _FakeClient(register=register)
    sink = _RecordingSink()

    with pytest.raises(NoAtRiskRelativesError, match="first- or second-degree"):
        _service(client, sink).generate_letters(
            CascadeRequest(pedigree_id=_PEDIGREE_ID, template_override=None, dry_run=False)
        )
