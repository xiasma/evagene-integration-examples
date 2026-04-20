"""Domain value objects returned by the LLM extractor.

These mirror the fields the ``family-history-intake-form`` demo captures
by hand, so the writer can reuse the same add-relative orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BiologicalSex(str, Enum):
    FEMALE = "female"
    MALE = "male"
    UNKNOWN = "unknown"


class SiblingRelation(str, Enum):
    SISTER = "sister"
    BROTHER = "brother"
    HALF_SISTER = "half_sister"
    HALF_BROTHER = "half_brother"


@dataclass(frozen=True)
class ProbandEntry:
    display_name: str
    biological_sex: BiologicalSex
    year_of_birth: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class RelativeEntry:
    display_name: str
    year_of_birth: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class SiblingEntry:
    display_name: str
    relation: SiblingRelation
    year_of_birth: int | None = None
    notes: str | None = None

    @property
    def biological_sex(self) -> BiologicalSex:
        if self.relation in (SiblingRelation.SISTER, SiblingRelation.HALF_SISTER):
            return BiologicalSex.FEMALE
        return BiologicalSex.MALE


@dataclass(frozen=True)
class ExtractedFamily:
    proband: ProbandEntry
    mother: RelativeEntry | None = None
    father: RelativeEntry | None = None
    maternal_grandmother: RelativeEntry | None = None
    maternal_grandfather: RelativeEntry | None = None
    paternal_grandmother: RelativeEntry | None = None
    paternal_grandfather: RelativeEntry | None = None
    siblings: tuple[SiblingEntry, ...] = field(default_factory=tuple)
