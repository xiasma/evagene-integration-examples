"""Fan out across every pedigree, diff against the store, notify on change.

The orchestrator owns the loop.  Every collaborator is injected — the
Evagene client, the store, the notifier, the clock, and the
rate-limiting sleeper — which keeps the unit test a simple table-driven
walk over fake doubles.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

from .evagene_client import PedigreeSummary
from .evaluator import ChangeEvent, diff_state
from .nice_parser import NiceResult, parse_nice_response
from .notifier import Notification, Notifier
from .state_store import AppendEventArgs, StateStore, StoredState, UpsertArgs

INTER_CALL_DELAY_SECONDS = 0.2


class NiceSource(Protocol):
    def list_pedigrees(self) -> list[PedigreeSummary]: ...

    def calculate_nice(self, pedigree_id: str) -> dict[str, object]: ...


class Clock(Protocol):
    def now_iso(self) -> str: ...


@dataclass(frozen=True)
class RunSummary:
    pedigrees_checked: int
    changes_detected: int


class Orchestrator:
    def __init__(
        self,
        *,
        source: NiceSource,
        store: StateStore,
        notifier: Notifier,
        clock: Clock,
        sleep: Callable[[float], None],
        dry_run: bool,
    ) -> None:
        self._source = source
        self._store = store
        self._notifier = notifier
        self._clock = clock
        self._sleep = sleep
        self._dry_run = dry_run

    def run(self) -> RunSummary:
        return self._walk(emit_events=True)

    def seed(self) -> RunSummary:
        return self._walk(emit_events=False)

    def _walk(self, *, emit_events: bool) -> RunSummary:
        pedigrees = self._source.list_pedigrees()
        changes = 0
        for index, summary in enumerate(pedigrees):
            if index > 0:
                self._sleep(INTER_CALL_DELAY_SECONDS)
            if self._process_one(summary, emit_events=emit_events):
                changes += 1
        return RunSummary(pedigrees_checked=len(pedigrees), changes_detected=changes)

    def _process_one(self, summary: PedigreeSummary, *, emit_events: bool) -> bool:
        payload = self._source.calculate_nice(summary.pedigree_id)
        result = parse_nice_response(payload)
        previous = self._store.get_state(summary.pedigree_id)

        change = diff_state(summary.pedigree_id, previous, result) if emit_events else None

        if not self._dry_run:
            self._persist(summary, result, change)

        if change is not None:
            self._notifier.notify(Notification(event=change, pedigree_label=summary.display_name))
            return True
        return False

    def _persist(
        self,
        summary: PedigreeSummary,
        result: NiceResult,
        change: ChangeEvent | None,
    ) -> None:
        now = self._clock.now_iso()
        self._store.upsert_state(
            UpsertArgs(
                pedigree_id=summary.pedigree_id,
                category=result.category.value,
                triggers=result.triggers,
                recorded_at=now,
            ),
        )
        if change is not None:
            self._store.append_event(
                AppendEventArgs(
                    pedigree_id=change.pedigree_id,
                    old_category=change.old_category,
                    new_category=change.new_category,
                    triggers_added=change.triggers_added,
                    triggers_removed=change.triggers_removed,
                    recorded_at=now,
                ),
            )


def previous_state_for(
    store: StateStore,
    pedigrees: Iterable[PedigreeSummary],
) -> dict[str, StoredState]:
    """Helper used by the history view — kept here so the orchestrator owns store reads."""
    resolved: dict[str, StoredState] = {}
    for pedigree in pedigrees:
        state = store.get_state(pedigree.pedigree_id)
        if state is not None:
            resolved[pedigree.pedigree_id] = state
    return resolved
