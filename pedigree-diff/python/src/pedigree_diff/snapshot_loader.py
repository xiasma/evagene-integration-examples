"""Load a :class:`PedigreeSnapshot` from either a UUID (live fetch) or a JSON file.

Responsible for exactly two things:

* dispatching to the right source (API vs filesystem);
* normalising the raw ``PedigreeDetail`` dict into the demo's value
  objects so the diff engine never sees raw JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from .config import SnapshotSource
from .snapshot import (
    DiseaseRecord,
    IndividualSnapshot,
    ParentChildLink,
    PartnerLink,
    PedigreeSnapshot,
)


class SnapshotFileError(ValueError):
    """Raised when a snapshot file is missing, unreadable, or malformed."""


class PedigreeDetailFetcher(Protocol):
    def get_pedigree_detail(self, pedigree_id: str) -> dict[str, Any]: ...


class SnapshotLoader:
    def __init__(self, fetcher: PedigreeDetailFetcher | None) -> None:
        self._fetcher = fetcher

    def load(self, source: SnapshotSource) -> PedigreeSnapshot:
        payload = self._fetch_payload(source)
        return normalise_pedigree_detail(payload)

    def _fetch_payload(self, source: SnapshotSource) -> dict[str, Any]:
        if source.pedigree_id is not None:
            if self._fetcher is None:
                raise SnapshotFileError(
                    "Cannot fetch pedigree by UUID: no API client was configured.",
                )
            return self._fetcher.get_pedigree_detail(source.pedigree_id)
        assert source.path is not None
        return _read_json_object(source.path)


def _read_json_object(path: str) -> dict[str, Any]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SnapshotFileError(f"Cannot read snapshot file {path!r}: {exc}") from exc
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise SnapshotFileError(f"Snapshot file {path!r} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SnapshotFileError(
            f"Snapshot file {path!r} must contain a JSON object at the top level.",
        )
    return parsed


def normalise_pedigree_detail(payload: dict[str, Any]) -> PedigreeSnapshot:
    """Project a raw Evagene ``PedigreeDetail`` onto the demo's value objects."""
    individuals = tuple(
        _individual_from(raw) for raw in _list_of_dicts(payload, "individuals")
    )
    proband_id = _find_proband_id(payload, individuals)
    partner_links = _partner_links_from(payload)
    parent_child_links = _parent_child_links_from(payload)
    return PedigreeSnapshot(
        pedigree_id=_str(payload.get("id")),
        display_name=_str(payload.get("display_name")),
        proband_id=proband_id,
        individuals=individuals,
        partner_links=partner_links,
        parent_child_links=parent_child_links,
    )


def _individual_from(raw: dict[str, Any]) -> IndividualSnapshot:
    events = _list_of_dicts(raw, "events")
    properties = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
    assert isinstance(properties, dict)
    return IndividualSnapshot(
        id=_str(raw.get("id")),
        display_name=_str(raw.get("display_name")),
        biological_sex=_str(raw.get("biological_sex")),
        date_of_birth=_first_event_date(events, "birth"),
        death_status=_str(properties.get("death_status")),
        diseases=tuple(_disease_from(d) for d in _list_of_dicts(raw, "diseases")),
        is_proband=_truthy_proband(raw.get("proband")),
    )


def _disease_from(raw: dict[str, Any]) -> DiseaseRecord:
    manifestations = _list_of_dicts(raw, "manifestations")
    return DiseaseRecord(
        disease_id=_str(raw.get("disease_id")),
        affection_status=_str(raw.get("affection_status")),
        age_at_diagnosis=_first_manifestation_age(manifestations),
    )


_PARTNER_PAIR_SIZE = 2


def _partner_links_from(payload: dict[str, Any]) -> frozenset[PartnerLink]:
    links: set[PartnerLink] = set()
    for relationship in _list_of_dicts(payload, "relationships"):
        members_raw = relationship.get("members")
        if not isinstance(members_raw, list):
            continue
        members = [_str(m) for m in members_raw if isinstance(m, str) and m]
        if len(members) == _PARTNER_PAIR_SIZE:
            links.add(PartnerLink.of(members[0], members[1]))
    return frozenset(links)


def _parent_child_links_from(payload: dict[str, Any]) -> frozenset[ParentChildLink]:
    relationship_members: dict[str, list[str]] = {}
    for relationship in _list_of_dicts(payload, "relationships"):
        rid = _str(relationship.get("id"))
        members_raw = relationship.get("members")
        if rid and isinstance(members_raw, list):
            relationship_members[rid] = [
                _str(m) for m in members_raw if isinstance(m, str) and m
            ]

    links: set[ParentChildLink] = set()
    for egg in _list_of_dicts(payload, "eggs"):
        child_id = _str(egg.get("individual_id"))
        relationship_id = _str(egg.get("relationship_id"))
        if not child_id or not relationship_id:
            continue
        for parent_id in relationship_members.get(relationship_id, ()):
            if parent_id:
                links.add(ParentChildLink(parent_id=parent_id, child_id=child_id))
    return frozenset(links)


def _find_proband_id(
    payload: dict[str, Any],
    individuals: tuple[IndividualSnapshot, ...],
) -> str | None:
    declared = payload.get("proband_id")
    if isinstance(declared, str) and declared:
        return declared
    for individual in individuals:
        if individual.is_proband:
            return individual.id
    return None


def _first_event_date(events: list[dict[str, Any]], event_type: str) -> str | None:
    for event in events:
        if _str(event.get("type")) == event_type:
            start = event.get("date_start")
            if isinstance(start, str) and start:
                return start
    return None


def _first_manifestation_age(manifestations: list[dict[str, Any]]) -> int | None:
    for manifestation in manifestations:
        age = manifestation.get("age_of_onset")
        if isinstance(age, int):
            return age
    return None


def _list_of_dicts(container: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _truthy_proband(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return False
