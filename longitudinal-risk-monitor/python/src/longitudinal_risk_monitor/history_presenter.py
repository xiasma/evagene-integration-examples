"""Format recorded events for the ``history`` subcommand."""

from __future__ import annotations

import json
from typing import TextIO

from .config import HistoryFormat
from .state_store import StoredEvent


def present(events: list[StoredEvent], output_format: HistoryFormat, sink: TextIO) -> None:
    if output_format is HistoryFormat.JSON:
        sink.write(json.dumps([_to_jsonable(event) for event in events], indent=2) + "\n")
        return
    if not events:
        sink.write("No events recorded.\n")
        return
    for event in events:
        sink.write(_format_text_line(event) + "\n")


def _format_text_line(event: StoredEvent) -> str:
    base = (
        f"{event.recorded_at}  {event.pedigree_id}  "
        f"{event.old_category} -> {event.new_category}"
    )
    extras: list[str] = []
    if event.triggers_added:
        extras.append("added: " + "; ".join(event.triggers_added))
    if event.triggers_removed:
        extras.append("removed: " + "; ".join(event.triggers_removed))
    return base + (" | " + " | ".join(extras) if extras else "")


def _to_jsonable(event: StoredEvent) -> dict[str, object]:
    return {
        "id": event.id,
        "pedigree_id": event.pedigree_id,
        "old_category": event.old_category,
        "new_category": event.new_category,
        "triggers_added": list(event.triggers_added),
        "triggers_removed": list(event.triggers_removed),
        "recorded_at": event.recorded_at,
    }
