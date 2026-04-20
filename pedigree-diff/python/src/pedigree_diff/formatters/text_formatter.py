"""Human-readable text formatter (with optional ANSI colour when the sink is a TTY)."""

from __future__ import annotations

from datetime import date, datetime
from typing import TextIO

from ..diff_engine import (
    AddedIndividual,
    Diff,
    DiseaseChange,
    FieldChange,
    FieldChangeKind,
    ParentChildLinkChange,
    PartnerLinkChange,
    ProbandChange,
    RemovedIndividual,
    UpdatedIndividual,
)
from ..relationship_labeler import label_relationship
from ..snapshot import DiseaseRecord, IndividualSnapshot, PedigreeSnapshot
from .base import FormatOptions

_GREEN = "\x1b[32m"
_RED = "\x1b[31m"
_YELLOW = "\x1b[33m"
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"


class TextFormatter:
    def render(
        self,
        diff: Diff,
        before: PedigreeSnapshot,
        after: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None:
        self._write_header(after, options, sink)

        for added in diff.added:
            self._write_added(added, after, options, sink)
            sink.write("\n")
        for updated in diff.updated:
            self._write_updated(updated, after, options, sink)
            sink.write("\n")
        for removed in diff.removed:
            self._write_removed(removed, before, options, sink)
            sink.write("\n")

        if diff.proband_change is not None:
            self._write_proband_change(diff.proband_change, before, after, sink)

        self._write_link_changes(
            diff.partner_link_changes,
            diff.parent_child_link_changes,
            before,
            after,
            sink,
        )

        if options.include_unchanged:
            self._write_unchanged(diff, after, sink)

        if not diff.has_changes() and not options.include_unchanged:
            sink.write("No changes.\n")

    def _write_header(
        self,
        snapshot: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None:
        if options.since is None:
            return
        days = _days_since(options.since, options.today)
        day_word = "day" if days == 1 else "days"
        sink.write(f"Since {options.since.date().isoformat()} ({days} {day_word}):\n\n")

    def _write_added(
        self,
        added: AddedIndividual,
        after: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None:
        individual = added.individual
        label = label_relationship(after, individual.id)
        headline = (
            f"+ Added: {individual.display_name} "
            f"({label}{_age_suffix(individual, options.today)})"
        )
        sink.write(self._colour(headline, _GREEN, options) + "\n")
        for disease in individual.diseases:
            sink.write(
                self._colour(
                    f"  + Diagnosed with {_disease_phrase(disease)}",
                    _GREEN,
                    options,
                )
                + "\n",
            )

    def _write_removed(
        self,
        removed: RemovedIndividual,
        before: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None:
        individual = removed.individual
        label = label_relationship(before, individual.id)
        affection = _affected_summary(individual)
        suffix = f", {affection}" if affection else ""
        headline = f"- Removed: {individual.display_name} ({label}{suffix})"
        sink.write(self._colour(headline, _RED, options) + "\n")

    def _write_updated(
        self,
        updated: UpdatedIndividual,
        after: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None:
        individual = updated.after
        label = label_relationship(after, individual.id)
        headline = f"~ Updated: {individual.display_name} ({label})"
        sink.write(self._colour(headline, _YELLOW, options) + "\n")
        for field_change in updated.field_changes:
            sink.write(f"  - {_describe_field_change(field_change)}\n")
        for disease_change in _filter_disease_changes(
            updated.disease_changes,
            updated.after,
            options.since,
        ):
            marker = "+" if disease_change.added else "-"
            verb = "Diagnosed with" if disease_change.added else "No longer recorded:"
            sink.write(f"  {marker} {verb} {_disease_phrase(disease_change.disease)}\n")

    def _write_proband_change(
        self,
        change: ProbandChange,
        before: PedigreeSnapshot,
        after: PedigreeSnapshot,
        sink: TextIO,
    ) -> None:
        before_name = _name_for(change.before, before)
        after_name = _name_for(change.after, after)
        sink.write(f"~ Proband changed: {before_name} -> {after_name}\n")

    def _write_link_changes(
        self,
        partner_changes: tuple[PartnerLinkChange, ...],
        parent_child_changes: tuple[ParentChildLinkChange, ...],
        before: PedigreeSnapshot,
        after: PedigreeSnapshot,
        sink: TextIO,
    ) -> None:
        by_id = _union_names(before, after)
        for partner in partner_changes:
            marker = "+" if partner.added else "-"
            verb = "Partner link added" if partner.added else "Partner link removed"
            a = by_id.get(partner.link.left, partner.link.left)
            b = by_id.get(partner.link.right, partner.link.right)
            sink.write(f"{marker} {verb}: {a} <-> {b}\n")
        for pc in parent_child_changes:
            marker = "+" if pc.added else "-"
            verb = "Parent link added" if pc.added else "Parent link removed"
            parent = by_id.get(pc.link.parent_id, pc.link.parent_id)
            child = by_id.get(pc.link.child_id, pc.link.child_id)
            sink.write(f"{marker} {verb}: {parent} -> {child}\n")

    def _write_unchanged(
        self,
        diff: Diff,
        after: PedigreeSnapshot,
        sink: TextIO,
    ) -> None:
        if not diff.unchanged:
            return
        sink.write("\nUnchanged:\n")
        for unchanged in diff.unchanged:
            label = label_relationship(after, unchanged.individual.id)
            sink.write(f"  = {unchanged.individual.display_name} ({label})\n")

    def _colour(self, text: str, code: str, options: FormatOptions) -> str:
        if not options.use_colour or not code:
            return text
        return f"{code}{_BOLD}{text}{_RESET}"


def _describe_field_change(change: FieldChange) -> str:
    labels = {
        FieldChangeKind.NAME: "Name updated",
        FieldChangeKind.DATE_OF_BIRTH: "Date of birth corrected",
        FieldChangeKind.BIOLOGICAL_SEX: "Biological sex updated",
        FieldChangeKind.DEATH_STATUS: "Death status updated",
    }
    before = change.before or "(empty)"
    after = change.after or "(empty)"
    return f"{labels[change.kind]}: {before} -> {after}"


def _disease_phrase(disease: DiseaseRecord) -> str:
    base = disease.disease_id or "unspecified condition"
    parts: list[str] = [base]
    if disease.affection_status and disease.affection_status != "affected":
        parts.append(f"({disease.affection_status})")
    if disease.age_at_diagnosis is not None:
        parts.append(f"age {disease.age_at_diagnosis}")
    return ", ".join(parts) if len(parts) > 1 else parts[0]


def _affected_summary(individual: IndividualSnapshot) -> str:
    affected = [d for d in individual.diseases if d.affection_status == "affected"]
    if not affected:
        return ""
    names = ", ".join(d.disease_id or "unspecified" for d in affected)
    return f"was recorded as affected with {names}"


def _age_suffix(individual: IndividualSnapshot, today: date) -> str:
    age = _current_age(individual, today)
    return f", age {age}" if age is not None else ""


def _current_age(individual: IndividualSnapshot, today: date) -> int | None:
    if not individual.date_of_birth:
        return None
    try:
        birth = date.fromisoformat(individual.date_of_birth)
    except ValueError:
        return None
    years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    return years if years >= 0 else None


def _name_for(individual_id: str | None, snapshot: PedigreeSnapshot) -> str:
    if individual_id is None:
        return "(none)"
    for individual in snapshot.individuals:
        if individual.id == individual_id:
            return individual.display_name or individual_id
    return individual_id


def _union_names(before: PedigreeSnapshot, after: PedigreeSnapshot) -> dict[str, str]:
    names: dict[str, str] = {ind.id: ind.display_name for ind in before.individuals}
    for ind in after.individuals:
        names[ind.id] = ind.display_name
    return names


def _filter_disease_changes(
    changes: tuple[DiseaseChange, ...],
    individual: IndividualSnapshot,
    since: datetime | None,
) -> tuple[DiseaseChange, ...]:
    if since is None:
        return changes
    birth_year = _birth_year(individual)
    if birth_year is None:
        return changes
    cutoff_year = since.year
    return tuple(
        change for change in changes if _emerges_since(change, birth_year, cutoff_year)
    )


def _emerges_since(change: DiseaseChange, birth_year: int, cutoff_year: int) -> bool:
    year = _diagnosis_year(change.disease, birth_year)
    return year is None or year >= cutoff_year


def _birth_year(individual: IndividualSnapshot) -> int | None:
    if not individual.date_of_birth:
        return None
    try:
        return date.fromisoformat(individual.date_of_birth).year
    except ValueError:
        return None


def _diagnosis_year(disease: DiseaseRecord, birth_year: int) -> int | None:
    if disease.age_at_diagnosis is None:
        return None
    return birth_year + disease.age_at_diagnosis


def _days_since(since: datetime, today: date) -> int:
    since_date = since.date() if isinstance(since, datetime) else since
    return (today - since_date).days
