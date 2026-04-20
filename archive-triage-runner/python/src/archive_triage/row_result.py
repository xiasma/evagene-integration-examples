"""Value object for one CSV row per input pedigree."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RowResult:
    pedigree_id: str
    proband_name: str
    category: str
    refer_for_genetics: bool | None
    triggers_matched_count: int
    error: str
