from longitudinal_risk_monitor.evaluator import diff_state
from longitudinal_risk_monitor.nice_parser import NiceCategory, NiceResult
from longitudinal_risk_monitor.state_store import StoredState

_PEDIGREE_ID = "11111111-1111-1111-1111-111111111111"


def _stored(category: str, triggers: tuple[str, ...]) -> StoredState:
    return StoredState(
        pedigree_id=_PEDIGREE_ID,
        category=category,
        triggers=triggers,
        recorded_at="2026-04-20T00:00:00Z",
    )


def test_first_sighting_emits_no_change() -> None:
    current = NiceResult(NiceCategory.NEAR_POPULATION, ())

    assert diff_state(_PEDIGREE_ID, previous=None, current=current) is None


def test_unchanged_category_and_triggers_emits_no_change() -> None:
    triggers = ("Single first-degree relative with breast cancer <40.",)
    event = diff_state(
        _PEDIGREE_ID,
        previous=_stored("moderate", triggers),
        current=NiceResult(NiceCategory.MODERATE, triggers),
    )

    assert event is None


def test_category_change_records_added_triggers() -> None:
    event = diff_state(
        _PEDIGREE_ID,
        previous=_stored("near_population", ()),
        current=NiceResult(
            NiceCategory.MODERATE,
            ("Single first-degree relative with breast cancer <40.",),
        ),
    )

    assert event is not None
    assert event.old_category == "near_population"
    assert event.new_category == "moderate"
    assert event.triggers_added == ("Single first-degree relative with breast cancer <40.",)
    assert event.triggers_removed == ()


def test_same_category_new_trigger_added_still_emits_event() -> None:
    old = ("Existing trigger.",)
    new = ("Existing trigger.", "New trigger fired.")
    event = diff_state(
        _PEDIGREE_ID,
        previous=_stored("moderate", old),
        current=NiceResult(NiceCategory.MODERATE, new),
    )

    assert event is not None
    assert event.old_category == event.new_category == "moderate"
    assert event.triggers_added == ("New trigger fired.",)
    assert event.triggers_removed == ()


def test_trigger_removed_is_reported_in_removed_list() -> None:
    event = diff_state(
        _PEDIGREE_ID,
        previous=_stored("moderate", ("A.", "B.")),
        current=NiceResult(NiceCategory.MODERATE, ("A.",)),
    )

    assert event is not None
    assert event.triggers_added == ()
    assert event.triggers_removed == ("B.",)


def test_trigger_order_does_not_affect_equality() -> None:
    event = diff_state(
        _PEDIGREE_ID,
        previous=_stored("moderate", ("A.", "B.")),
        current=NiceResult(NiceCategory.MODERATE, ("B.", "A.")),
    )

    assert event is None
