"""Deterministic JSON formatter — stable key order, pretty-printed."""

from __future__ import annotations

import json
from typing import Any, TextIO

from ..diff_engine import (
    Diff,
    DiseaseChange,
    FieldChange,
    ParentChildLinkChange,
    PartnerLinkChange,
    UpdatedIndividual,
)
from ..relationship_labeler import label_relationship
from ..snapshot import DiseaseRecord, IndividualSnapshot, PedigreeSnapshot
from .base import FormatOptions


class JsonFormatter:
    def render(
        self,
        diff: Diff,
        before: PedigreeSnapshot,
        after: PedigreeSnapshot,
        options: FormatOptions,
        sink: TextIO,
    ) -> None:
        document: dict[str, Any] = {
            "added": [_individual_entry(a.individual, after) for a in diff.added],
            "removed": [_individual_entry(r.individual, before) for r in diff.removed],
            "updated": [_updated_entry(u, after) for u in diff.updated],
            "partner_links": [_partner_entry(c) for c in diff.partner_link_changes],
            "parent_child_links": [_parent_child_entry(c) for c in diff.parent_child_link_changes],
        }
        if diff.proband_change is not None:
            document["proband_change"] = {
                "before": diff.proband_change.before,
                "after": diff.proband_change.after,
            }
        if options.since is not None:
            document["since"] = options.since.isoformat()
        if options.include_unchanged:
            document["unchanged"] = [
                _individual_entry(u.individual, after) for u in diff.unchanged
            ]
        json.dump(document, sink, indent=2, sort_keys=True)
        sink.write("\n")


def _individual_entry(
    individual: IndividualSnapshot,
    snapshot: PedigreeSnapshot,
) -> dict[str, Any]:
    return {
        "id": individual.id,
        "display_name": individual.display_name,
        "biological_sex": individual.biological_sex,
        "date_of_birth": individual.date_of_birth,
        "death_status": individual.death_status,
        "relationship_to_proband": label_relationship(snapshot, individual.id),
        "diseases": [_disease_entry(d) for d in individual.diseases],
    }


def _updated_entry(
    updated: UpdatedIndividual,
    after: PedigreeSnapshot,
) -> dict[str, Any]:
    return {
        "id": updated.after.id,
        "display_name": updated.after.display_name,
        "relationship_to_proband": label_relationship(after, updated.after.id),
        "field_changes": [_field_change_entry(c) for c in updated.field_changes],
        "disease_changes": [_disease_change_entry(c) for c in updated.disease_changes],
    }


def _field_change_entry(change: FieldChange) -> dict[str, Any]:
    return {"kind": change.kind.value, "before": change.before, "after": change.after}


def _disease_change_entry(change: DiseaseChange) -> dict[str, Any]:
    return {
        "action": "added" if change.added else "removed",
        "disease": _disease_entry(change.disease),
    }


def _disease_entry(disease: DiseaseRecord) -> dict[str, Any]:
    return {
        "disease_id": disease.disease_id,
        "affection_status": disease.affection_status,
        "age_at_diagnosis": disease.age_at_diagnosis,
    }


def _partner_entry(change: PartnerLinkChange) -> dict[str, Any]:
    return {
        "action": "added" if change.added else "removed",
        "members": [change.link.left, change.link.right],
    }


def _parent_child_entry(change: ParentChildLinkChange) -> dict[str, Any]:
    return {
        "action": "added" if change.added else "removed",
        "parent_id": change.link.parent_id,
        "child_id": change.link.child_id,
    }
