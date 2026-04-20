"""Compose a per-relative Markdown letter and hand it to a sink.

Composition is local because the Evagene template-run endpoint operates
at pedigree level: it cannot vary its output per relative.  The
personalised salutation and relationship sentence are added here; the
template body is dropped in between.

The sink is an abstraction so tests can collect letters in memory while
production code writes them to disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .relative_selector import LetterTarget

_MAX_SLUG_LENGTH = 60
_NON_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class LetterFile:
    filename: str
    content: str


class LetterSink(Protocol):
    def write(self, letter: LetterFile) -> str:
        """Persist *letter* and return a path-like identifier for stdout reporting."""


class DiskLetterSink:
    """Write letters under *output_dir*; returns the POSIX-style path written."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def write(self, letter: LetterFile) -> str:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / letter.filename
        path.write_text(letter.content, encoding="utf-8")
        return path.as_posix()


def compose_letter(target: LetterTarget, template_body: str, index: int) -> LetterFile:
    return LetterFile(
        filename=_filename_for(target, index),
        content=_markdown_for(target, template_body),
    )


def _filename_for(target: LetterTarget, index: int) -> str:
    return f"{index:02d}-{_slugify(target.display_name)}.md"


def _slugify(name: str) -> str:
    lowered = name.strip().lower()
    slug = _NON_SLUG.sub("-", lowered).strip("-")
    if not slug:
        slug = "relative"
    return slug[:_MAX_SLUG_LENGTH].rstrip("-") or "relative"


def _markdown_for(target: LetterTarget, template_body: str) -> str:
    return (
        f"# Cascade screening invitation\n\n"
        f"Dear {target.display_name},\n\n"
        f"You are recorded as the **{target.relationship.lower()}** of the person "
        f"whose family has had a genetic result identified. The paragraphs below "
        f"were drafted automatically and should be reviewed by your genetic counsellor "
        f"before this letter is sent.\n\n"
        f"{template_body.rstrip()}\n\n"
        f"Yours sincerely,\n\n"
        f"The Clinical Genetics Team\n"
    )
