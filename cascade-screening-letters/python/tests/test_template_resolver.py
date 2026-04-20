from dataclasses import dataclass, field

from cascade_letters.evagene_client import CreateTemplateArgs, RegisterData, Template
from cascade_letters.template_resolver import DEFAULT_TEMPLATE_NAME, resolve_template_id


@dataclass
class _FakeClient:
    """Honours :class:`EvageneApi`; only ``list_templates`` / ``create_template`` are used."""

    templates: list[Template] = field(default_factory=list)
    created: list[CreateTemplateArgs] = field(default_factory=list)
    _next_id: int = 100

    def fetch_register(self, pedigree_id: str) -> RegisterData:
        raise AssertionError(f"resolver should not fetch the register (asked for {pedigree_id})")

    def list_templates(self) -> list[Template]:
        return list(self.templates)

    def create_template(self, args: CreateTemplateArgs) -> Template:
        self._next_id += 1
        new_id = f"99999999-9999-9999-9999-{self._next_id:012d}"
        created = Template(id=new_id, name=args.name)
        self.templates.append(created)
        self.created.append(args)
        return created

    def run_template(self, template_id: str, pedigree_id: str) -> str:
        raise AssertionError(
            f"resolver should not run a template (asked for {template_id}, {pedigree_id})"
        )


def test_honours_explicit_override_without_calling_the_api() -> None:
    client = _FakeClient(templates=[Template(id="ignored", name=DEFAULT_TEMPLATE_NAME)])

    template_id = resolve_template_id(client, override="explicit-id")

    assert template_id == "explicit-id"
    assert client.created == []


def test_returns_existing_template_when_found_by_name() -> None:
    existing = Template(id="existing-id", name=DEFAULT_TEMPLATE_NAME)
    client = _FakeClient(templates=[Template(id="other", name="other"), existing])

    template_id = resolve_template_id(client, override=None)

    assert template_id == "existing-id"
    assert client.created == []


def test_creates_template_when_none_match_by_name() -> None:
    client = _FakeClient(templates=[Template(id="other", name="other")])

    template_id = resolve_template_id(client, override=None)

    assert template_id.startswith("99999999-")
    assert len(client.created) == 1
    assert client.created[0].name == DEFAULT_TEMPLATE_NAME
    assert "{{proband_name}}" in client.created[0].user_prompt_template
    assert "{{disease_list}}" in client.created[0].user_prompt_template


def test_custom_name_is_used_for_lookup_and_creation() -> None:
    client = _FakeClient()

    resolve_template_id(client, override=None, name="my-template")

    assert client.created[0].name == "my-template"
