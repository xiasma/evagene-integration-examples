import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from longitudinal_risk_monitor.evagene_client import PedigreeSummary
from longitudinal_risk_monitor.notifier import Notification
from longitudinal_risk_monitor.orchestrator import INTER_CALL_DELAY_SECONDS, Orchestrator
from longitudinal_risk_monitor.state_store import StateStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

_PEDIGREES = [
    PedigreeSummary("11111111-1111-1111-1111-111111111111", "Ashton family"),
    PedigreeSummary("22222222-2222-2222-2222-222222222222", "Blake family"),
    PedigreeSummary("33333333-3333-3333-3333-333333333333", "Carter family"),
    PedigreeSummary("44444444-4444-4444-4444-444444444444", "Davies family"),
    PedigreeSummary("55555555-5555-5555-5555-555555555555", "Evans family"),
]


def _load_fixture(name: str) -> dict[str, Any]:
    payload: Any = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


_GREEN = _load_fixture("sample-nice-green.json")
_AMBER = _load_fixture("sample-nice-amber.json")
_RED = _load_fixture("sample-nice-red.json")


class _FakeSource:
    def __init__(self, pedigrees: list[PedigreeSummary], payloads: dict[str, dict[str, Any]]):
        self._pedigrees = pedigrees
        self._payloads = payloads
        self.calculate_calls: list[str] = []

    def list_pedigrees(self) -> list[PedigreeSummary]:
        return list(self._pedigrees)

    def calculate_nice(self, pedigree_id: str) -> dict[str, Any]:
        self.calculate_calls.append(pedigree_id)
        return self._payloads[pedigree_id]


class _FrozenClock:
    def now_iso(self) -> str:
        return "2026-04-20T00:00:00.000000Z"


class _SpyNotifier:
    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    def notify(self, notification: Notification) -> None:
        self.notifications.append(notification)


@pytest.fixture()
def store(tmp_path: Path) -> Iterator[StateStore]:
    s = StateStore(str(tmp_path / "state.db"))
    try:
        yield s
    finally:
        s.close()


def _baseline_payloads() -> dict[str, dict[str, Any]]:
    return {
        _PEDIGREES[0].pedigree_id: _GREEN,
        _PEDIGREES[1].pedigree_id: _GREEN,
        _PEDIGREES[2].pedigree_id: _GREEN,
        _PEDIGREES[3].pedigree_id: _AMBER,
        _PEDIGREES[4].pedigree_id: _RED,
    }


def _build_orchestrator(
    source: _FakeSource,
    store: StateStore,
    notifier: _SpyNotifier,
    sleeps: list[float],
    *,
    dry_run: bool = False,
) -> Orchestrator:
    return Orchestrator(
        source=source,
        store=store,
        notifier=notifier,
        clock=_FrozenClock(),
        sleep=sleeps.append,
        dry_run=dry_run,
    )


def test_seed_populates_baseline_and_emits_no_events(store: StateStore) -> None:
    source = _FakeSource(_PEDIGREES, _baseline_payloads())
    notifier = _SpyNotifier()
    sleeps: list[float] = []

    summary = _build_orchestrator(source, store, notifier, sleeps).seed()

    assert summary.pedigrees_checked == 5
    assert summary.changes_detected == 0
    assert notifier.notifications == []
    for pedigree in _PEDIGREES:
        assert store.get_state(pedigree.pedigree_id) is not None
    assert store.list_events(None) == []


def test_seed_then_run_with_no_changes_emits_no_events(store: StateStore) -> None:
    payloads = _baseline_payloads()
    source = _FakeSource(_PEDIGREES, payloads)
    notifier = _SpyNotifier()
    sleeps: list[float] = []

    _build_orchestrator(source, store, notifier, sleeps).seed()
    summary = _build_orchestrator(source, store, _SpyNotifier(), sleeps).run()

    assert summary.changes_detected == 0
    assert notifier.notifications == []


def test_run_across_five_pedigrees_fires_single_notification_when_one_changed(
    store: StateStore,
) -> None:
    # Seed baseline where all are GREEN except one pedigree is AMBER.
    seed_payloads = dict.fromkeys([p.pedigree_id for p in _PEDIGREES], _GREEN)
    seed_payloads[_PEDIGREES[3].pedigree_id] = _AMBER
    source = _FakeSource(_PEDIGREES, seed_payloads)
    sleeps: list[float] = []
    _build_orchestrator(source, store, _SpyNotifier(), sleeps).seed()

    # Today, pedigree[2] has flipped from GREEN to AMBER.
    today_payloads = dict(seed_payloads)
    today_payloads[_PEDIGREES[2].pedigree_id] = _AMBER
    today_source = _FakeSource(_PEDIGREES, today_payloads)
    notifier = _SpyNotifier()
    sleeps.clear()

    summary = _build_orchestrator(today_source, store, notifier, sleeps).run()

    assert summary.pedigrees_checked == 5
    assert summary.changes_detected == 1
    assert len(notifier.notifications) == 1
    changed = notifier.notifications[0]
    assert changed.event.pedigree_id == _PEDIGREES[2].pedigree_id
    assert changed.event.old_category == "near_population"
    assert changed.event.new_category == "moderate"
    assert changed.pedigree_label == "Carter family"


def test_run_sleeps_between_each_pedigree_but_not_before_the_first(store: StateStore) -> None:
    source = _FakeSource(_PEDIGREES, _baseline_payloads())
    sleeps: list[float] = []

    _build_orchestrator(source, store, _SpyNotifier(), sleeps).seed()

    assert sleeps == [INTER_CALL_DELAY_SECONDS] * (len(_PEDIGREES) - 1)


def test_dry_run_does_not_mutate_the_store(store: StateStore) -> None:
    source = _FakeSource(_PEDIGREES, _baseline_payloads())
    sleeps: list[float] = []

    _build_orchestrator(source, store, _SpyNotifier(), sleeps, dry_run=True).run()

    for pedigree in _PEDIGREES:
        assert store.get_state(pedigree.pedigree_id) is None


def test_run_emits_event_after_forced_state_mismatch(store: StateStore) -> None:
    # Seed with the genuine state, then corrupt one row to GREEN even though
    # today's calculation says AMBER.  This mirrors the live smoke step 3.
    source = _FakeSource(_PEDIGREES, _baseline_payloads())
    sleeps: list[float] = []
    _build_orchestrator(source, store, _SpyNotifier(), sleeps).seed()

    target_id = _PEDIGREES[3].pedigree_id  # baseline AMBER
    from longitudinal_risk_monitor.state_store import UpsertArgs
    store.upsert_state(UpsertArgs(target_id, "near_population", (), "2026-04-19T00:00:00Z"))

    notifier = _SpyNotifier()
    sleeps.clear()
    summary = _build_orchestrator(
        _FakeSource(_PEDIGREES, _baseline_payloads()), store, notifier, sleeps,
    ).run()

    assert summary.changes_detected == 1
    assert notifier.notifications[0].event.pedigree_id == target_id
    assert notifier.notifications[0].event.new_category == "moderate"
    events = store.list_events(target_id)
    assert len(events) == 1
