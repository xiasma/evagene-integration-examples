"""Markdown formatter — designed for pasting into a referral letter."""

from __future__ import annotations

from typing import TextIO

from ..diff_engine import (
    Diff,
    DiseaseChange,
    FieldChange,
    FieldChangeKind,
    ParentChildLinkChange,
    PartnerLinkChange,
)
from ..relationship_labeler import label_relationship
from ..snapshot import DiseaseRecord, IndividualSnapshot, PedigreeSnapshot
from .base import FormatOptions


class MarkdownFormatter:
    def render(
        self,
        diff: Diff,
        before: PedigreeSnapshot,
        after: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None:
        _write_header(options, sink)
        _write_added(diff, after, sink)
        _write_removed(diff, before, sink)
        _write_updated(diff, after, sink)
        _write_proband_change(diff, before, after, sink)
        _write_link_sections(diff, before, after, sink)
        _write_unchanged(diff, after, options, sink)
        if not diff.has_changes() and not options.include_unchanged:
            sink.write("_No changes._\n")


def _write_header(options: FormatOptions, sink: TextIO) -> None:
    sink.write("# Pedigree change log\n\n")
    if options.since is not None:
        sink.write(f"_Changes since {options.since.date().isoformat()}._\n\n")


def _write_added(diff: Diff, after: PedigreeSnapshot, sink: TextIO) -> None:
    if not diff.added:
        return
    sink.write("## Added\n\n")
    for added in diff.added:
        _write_individual_bullet(added.individual, after, sink)
    sink.write("\n")


def _write_removed(diff: Diff, before: PedigreeSnapshot, sink: TextIO) -> None:
    if not diff.removed:
        return
    sink.write("## Removed\n\n")
    for removed in diff.removed:
        label = label_relationship(before, removed.individual.id)
        affection = _affected_summary(removed.individual)
        suffix = f" \u2014 {affection}" if affection else ""
        sink.write(f"- **{removed.individual.display_name}** ({label}){suffix}\n")
    sink.write("\n")


def _write_updated(diff: Diff, after: PedigreeSnapshot, sink: TextIO) -> None:
    if not diff.updated:
        return
    sink.write("## Updated\n\n")
    for updated in diff.updated:
        label = label_relationship(after, updated.after.id)
        sink.write(f"- **{updated.after.display_name}** ({label})\n")
        for field_change in updated.field_changes:
            sink.write(f"  - {_describe_field_change(field_change)}\n")
        for disease_change in updated.disease_changes:
            sink.write(f"  - {_describe_disease_change(disease_change)}\n")
    sink.write("\n")


def _write_proband_change(
    diff: Diff,
    before: PedigreeSnapshot,
    after: PedigreeSnapshot,
    sink: TextIO,
) -> None:
    if diff.proband_change is None:
        return
    before_name = _name_for(diff.proband_change.before, before)
    after_name = _name_for(diff.proband_change.after, after)
    sink.write(f"## Proband changed\n\n- {before_name} -> {after_name}\n\n")


def _write_link_sections(
    diff: Diff,
    before: PedigreeSnapshot,
    after: PedigreeSnapshot,
    sink: TextIO,
) -> None:
    names = _union_names(before, after)
    if diff.partner_link_changes:
        sink.write("## Partner links\n\n")
        for partner_change in diff.partner_link_changes:
            sink.write(_partner_line(partner_change, names) + "\n")
        sink.write("\n")
    if diff.parent_child_link_changes:
        sink.write("## Parent-child links\n\n")
        for pc_change in diff.parent_child_link_changes:
            sink.write(_parent_child_line(pc_change, names) + "\n")
        sink.write("\n")


def _write_unchanged(
    diff: Diff,
    after: PedigreeSnapshot,
    options: FormatOptions,
    sink: TextIO,
) -> None:
    if not (options.include_unchanged and diff.unchanged):
        return
    sink.write("## Unchanged\n\n")
    for unchanged in diff.unchanged:
        label = label_relationship(after, unchanged.individual.id)
        sink.write(f"- {unchanged.individual.display_name} ({label})\n")
    sink.write("\n")


def _write_individual_bullet(
    individual: IndividualSnapshot,
    snapshot: PedigreeSnapshot,
    sink: TextIO,
) -> None:
    label = label_relationship(snapshot, individual.id)
    sink.write(f"- **{individual.display_name}** ({label})\n")
    for disease in individual.diseases:
        sink.write(f"  - Diagnosed with {_disease_phrase(disease)}\n")


def _describe_field_change(change: FieldChange) -> str:
    labels = {
        FieldChangeKind.NAME: "Name",
        FieldChangeKind.DATE_OF_BIRTH: "Date of birth",
        FieldChangeKind.BIOLOGICAL_SEX: "Biological sex",
        FieldChangeKind.DEATH_STATUS: "Death status",
    }
    return f"{labels[change.kind]}: {change.before or '(empty)'} -> {change.after or '(empty)'}"


def _describe_disease_change(change: DiseaseChange) -> str:
    verb = "Diagnosed with" if change.added else "No longer recorded:"
    return f"{verb} {_disease_phrase(change.disease)}"


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


def _name_for(individual_id: str | None, snapshot: PedigreeSnapshot) -> str:
    if individual_id is None:
        return "(none)"
    for individual in snapshot.individuals:
        if individual.id == individual_id:
            return individual.display_name or individual_id
    return individual_id


def _partner_line(change: PartnerLinkChange, names: dict[str, str]) -> str:
    verb = "added" if change.added else "removed"
    left = names.get(change.link.left, change.link.left)
    right = names.get(change.link.right, change.link.right)
    return f"- {verb}: {left} <-> {right}"


def _parent_child_line(change: ParentChildLinkChange, names: dict[str, str]) -> str:
    verb = "added" if change.added else "removed"
    parent = names.get(change.link.parent_id, change.link.parent_id)
    child = names.get(change.link.child_id, change.link.child_id)
    return f"- {verb}: {parent} -> {child}"


def _union_names(before: PedigreeSnapshot, after: PedigreeSnapshot) -> dict[str, str]:
    names: dict[str, str] = {ind.id: ind.display_name for ind in before.individuals}
    for ind in after.individuals:
        names[ind.id] = ind.display_name
    return names


