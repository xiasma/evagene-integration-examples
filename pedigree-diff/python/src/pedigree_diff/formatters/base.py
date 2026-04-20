"""Shared formatter protocol and options."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, TextIO

from ..diff_engine import Diff
from ..snapshot import PedigreeSnapshot


@dataclass(frozen=True)
class FormatOptions:
    include_unchanged: bool
    since: datetime | None
    use_colour: bool
    today: date


class Formatter(Protocol):
    def render(
        self,
        diff: Diff,
        before: PedigreeSnapshot,
        after: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None: ...
