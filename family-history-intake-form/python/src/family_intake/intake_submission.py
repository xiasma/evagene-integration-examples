"""Domain value object + parser for the intake form's submission.

Pure: takes a raw form mapping (as Flask delivers it in ``request.form``)
and returns either a validated :class:`IntakeSubmission` or raises an
:class:`IntakeValidationError` naming the field at fault.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

MIN_YEAR = 1850
MAX_YEAR = 2030
MAX_SIBLINGS = 4


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
class RelativeEntry:
    display_name: str
    year_of_birth: int | None = None


@dataclass(frozen=True)
class SiblingEntry:
    display_name: str
    relation: SiblingRelation
    biological_sex: BiologicalSex
    year_of_birth: int | None = None


@dataclass(frozen=True)
class ProbandEntry:
    display_name: str
    biological_sex: BiologicalSex
    year_of_birth: int | None = None


@dataclass(frozen=True)
class IntakeSubmission:
    proband: ProbandEntry
    mother: RelativeEntry | None = None
    father: RelativeEntry | None = None
    maternal_grandmother: RelativeEntry | None = None
    maternal_grandfather: RelativeEntry | None = None
    paternal_grandmother: RelativeEntry | None = None
    paternal_grandfather: RelativeEntry | None = None
    siblings: tuple[SiblingEntry, ...] = field(default_factory=tuple)


class IntakeValidationError(ValueError):
    """Raised when form data does not meet the intake schema."""


def parse_intake_submission(form: Mapping[str, str]) -> IntakeSubmission:
    """Parse a Flask-style form mapping into a validated submission."""
    return IntakeSubmission(
        proband=_parse_proband(form),
        mother=_optional_relative(form, "mother"),
        father=_optional_relative(form, "father"),
        maternal_grandmother=_optional_relative(form, "maternal_grandmother"),
        maternal_grandfather=_optional_relative(form, "maternal_grandfather"),
        paternal_grandmother=_optional_relative(form, "paternal_grandmother"),
        paternal_grandfather=_optional_relative(form, "paternal_grandfather"),
        siblings=_parse_siblings(form),
    )


def _parse_proband(form: Mapping[str, str]) -> ProbandEntry:
    name = form.get("proband_name", "").strip()
    if not name:
        raise IntakeValidationError("The patient's name is required.")
    return ProbandEntry(
        display_name=name,
        biological_sex=_parse_sex(form.get("proband_sex", "")),
        year_of_birth=_parse_year(form.get("proband_year", ""), "proband_year"),
    )


def _optional_relative(form: Mapping[str, str], prefix: str) -> RelativeEntry | None:
    name = form.get(f"{prefix}_name", "").strip()
    if not name:
        return None
    return RelativeEntry(
        display_name=name,
        year_of_birth=_parse_year(form.get(f"{prefix}_year", ""), f"{prefix}_year"),
    )


def _parse_siblings(form: Mapping[str, str]) -> tuple[SiblingEntry, ...]:
    siblings: list[SiblingEntry] = []
    for index in range(MAX_SIBLINGS):
        name = form.get(f"sibling_{index}_name", "").strip()
        if not name:
            continue
        relation = _parse_sibling_relation(form.get(f"sibling_{index}_relation", ""), index)
        siblings.append(
            SiblingEntry(
                display_name=name,
                relation=relation,
                biological_sex=_sex_for_sibling_relation(relation),
                year_of_birth=_parse_year(
                    form.get(f"sibling_{index}_year", ""),
                    f"sibling_{index}_year",
                ),
            )
        )
    return tuple(siblings)


def _parse_sex(raw: str) -> BiologicalSex:
    if not raw:
        return BiologicalSex.UNKNOWN
    try:
        return BiologicalSex(raw)
    except ValueError as exc:
        raise IntakeValidationError(f"Unknown biological sex: {raw!r}") from exc


def _parse_sibling_relation(raw: str, index: int) -> SiblingRelation:
    try:
        return SiblingRelation(raw)
    except ValueError as exc:
        raise IntakeValidationError(
            f"Sibling {index + 1} must have a relation "
            "(sister / brother / half_sister / half_brother)."
        ) from exc


def _sex_for_sibling_relation(relation: SiblingRelation) -> BiologicalSex:
    if relation in (SiblingRelation.SISTER, SiblingRelation.HALF_SISTER):
        return BiologicalSex.FEMALE
    return BiologicalSex.MALE


def _parse_year(raw: str, field_name: str) -> int | None:
    trimmed = raw.strip()
    if not trimmed:
        return None
    try:
        year = int(trimmed)
    except ValueError as exc:
        raise IntakeValidationError(
            f"Field {field_name!r} must be an integer year between {MIN_YEAR} and {MAX_YEAR}."
        ) from exc
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise IntakeValidationError(
            f"Field {field_name!r} must be a year between {MIN_YEAR} and {MAX_YEAR}; got {year}."
        )
    return year
