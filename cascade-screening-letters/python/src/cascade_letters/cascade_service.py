"""Orchestrator: selector + resolver + one template run + writer per relative.

Knows the sequence of calls but no HTTP and no filesystem.  The template
is executed once per pedigree — the endpoint does not accept a
per-individual target, so running it N times would produce N copies of
the same text and burn quota for nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .evagene_client import EvageneApi
from .letter_writer import LetterSink, compose_letter
from .relative_selector import LetterTarget, select_at_risk_relatives
from .template_resolver import resolve_template_id


class NoAtRiskRelativesError(RuntimeError):
    """Raised when the pedigree has no first- or second-degree relatives to write to."""


@dataclass(frozen=True)
class CascadeRequest:
    pedigree_id: str
    template_override: str | None
    dry_run: bool


@dataclass(frozen=True)
class CascadeResult:
    targets: tuple[LetterTarget, ...]
    written_paths: tuple[str, ...]


class CascadeService:
    def __init__(self, *, client: EvageneApi, sink: LetterSink) -> None:
        self._client = client
        self._sink = sink

    def generate_letters(self, request: CascadeRequest) -> CascadeResult:
        targets = self._select_targets(request.pedigree_id)
        if request.dry_run:
            return CascadeResult(targets=tuple(targets), written_paths=())

        template_body = self._render_template(request)
        written = tuple(
            self._sink.write(compose_letter(target, template_body, index))
            for index, target in enumerate(targets, start=1)
        )
        return CascadeResult(targets=tuple(targets), written_paths=written)

    def _select_targets(self, pedigree_id: str) -> list[LetterTarget]:
        register = self._client.fetch_register(pedigree_id)
        if register.proband_id is None:
            raise NoAtRiskRelativesError(
                f"Pedigree {pedigree_id} has no designated proband; "
                "set one in the Evagene web app before running this tool."
            )
        targets = select_at_risk_relatives(register)
        if not targets:
            raise NoAtRiskRelativesError(
                f"Pedigree {pedigree_id} has no first- or second-degree relatives "
                "with a display name recorded."
            )
        return targets

    def _render_template(self, request: CascadeRequest) -> str:
        template_id = resolve_template_id(self._client, request.template_override)
        return self._client.run_template(template_id, request.pedigree_id)
