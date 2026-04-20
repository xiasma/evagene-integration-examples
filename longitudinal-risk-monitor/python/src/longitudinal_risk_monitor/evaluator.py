"""Pure delta computation: stored state + new result → optional change event."""

from __future__ import annotations

from dataclasses import dataclass

from .nice_parser import NiceResult
from .state_store import StoredState


@dataclass(frozen=True)
class ChangeEvent:
    pedigree_id: str
    old_category: str
    new_category: str
    triggers_added: tuple[str, ...]
    triggers_removed: tuple[str, ...]


def diff_state(
    pedigree_id: str,
    previous: StoredState | None,
    current: NiceResult,
) -> ChangeEvent | None:
    """Return a :class:`ChangeEvent` if either category or trigger set has shifted.

    A first sighting (``previous is None``) is *not* a change — the
    orchestrator records the baseline but emits no event.
    """
    if previous is None:
        return None

    previous_triggers = frozenset(previous.triggers)
    current_triggers = frozenset(current.triggers)

    if previous.category == current.category.value and previous_triggers == current_triggers:
        return None

    return ChangeEvent(
        pedigree_id=pedigree_id,
        old_category=previous.category,
        new_category=current.category.value,
        triggers_added=_sorted_tuple(current_triggers - previous_triggers),
        triggers_removed=_sorted_tuple(previous_triggers - current_triggers),
    )


def _sorted_tuple(values: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(values))
