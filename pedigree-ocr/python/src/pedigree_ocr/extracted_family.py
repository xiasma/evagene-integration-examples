"""Domain value objects returned by the vision extractor.

A deliberate superset of the ``call-notes-to-pedigree`` shape. Every
individual carries an :class:`AffectionStatus` because that is the one
thing a drawing tells you that free-text notes usually do not -- which
squares and circles are filled in. The ``notes`` field is the escape
hatch for symbols the schema does not cover (MZ-twin chevrons,
double-line consanguinity, deceased slashes, question marks, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BiologicalSex(str, Enum):
    FEMALE = "female"
    MALE = "male"
    UNKNOWN = "unknown"


class AffectionStatus(str, Enum):
    CLEAR = "clear"
    AFFECTED = "affected"
    CARRIER = "carrier"
    PRESUMED_AFFECTED = "presumed-affected"


class SiblingRelation(str, Enum):
    SISTER = "sister"
    BROTHER = "brother"
    HALF_SISTER = "half_sister"
    HALF_BROTHER = "half_brother"


@dataclass(frozen=True)
class ProbandEntry:
    display_name: str
    biological_sex: BiologicalSex
    affection_status: AffectionStatus = AffectionStatus.CLEAR
    year_of_birth: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class RelativeEntry:
    display_name: str
    affection_status: AffectionStatus = AffectionStatus.CLEAR
    year_of_birth: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class SiblingEntry:
    display_name: str
    relation: SiblingRelation
    affection_status: AffectionStatus = AffectionStatus.CLEAR
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
