from pedigree_diff.diff_engine import (
    FieldChangeKind,
    diff_pedigrees,
)
from pedigree_diff.snapshot import (
    DiseaseRecord,
    IndividualSnapshot,
    ParentChildLink,
    PartnerLink,
    PedigreeSnapshot,
)


def _individual(
    ind_id: str,
    *,
    name: str = "Anon",
    sex: str = "female",
    dob: str | None = "1980-01-01",
    death_status: str = "alive",
    diseases: tuple[DiseaseRecord, ...] = (),
    proband: bool = False,
) -> IndividualSnapshot:
    return IndividualSnapshot(
        id=ind_id,
        display_name=name,
        biological_sex=sex,
        date_of_birth=dob,
        death_status=death_status,
        diseases=diseases,
        is_proband=proband,
    )


def _pedigree(
    *individuals: IndividualSnapshot,
    proband: str | None = None,
    partner_links: frozenset[PartnerLink] = frozenset(),
    parent_child_links: frozenset[ParentChildLink] = frozenset(),
) -> PedigreeSnapshot:
    return PedigreeSnapshot(
        pedigree_id="ped",
        display_name="test",
        proband_id=proband,
        individuals=individuals,
        partner_links=partner_links,
        parent_child_links=parent_child_links,
    )


def test_detects_added_individual() -> None:
    before = _pedigree(_individual("a"))
    after = _pedigree(_individual("a"), _individual("b", name="Bobby"))

    diff = diff_pedigrees(before, after)

    assert len(diff.added) == 1
    assert diff.added[0].individual.id == "b"
    assert diff.removed == ()


def test_detects_removed_individual() -> None:
    before = _pedigree(_individual("a"), _individual("b"))
    after = _pedigree(_individual("a"))

    diff = diff_pedigrees(before, after)

    assert len(diff.removed) == 1
    assert diff.removed[0].individual.id == "b"


def test_detects_name_change() -> None:
    before = _pedigree(_individual("a", name="Jane"))
    after = _pedigree(_individual("a", name="Jane Smith"))

    diff = diff_pedigrees(before, after)

    assert len(diff.updated) == 1
    kinds = [c.kind for c in diff.updated[0].field_changes]
    assert kinds == [FieldChangeKind.NAME]


def test_detects_dob_and_death_and_sex_changes_together() -> None:
    before = _pedigree(
        _individual("a", dob="1980-01-01", sex="female", death_status="alive"),
    )
    after = _pedigree(
        _individual("a", dob="1981-01-01", sex="male", death_status="dead"),
    )

    diff = diff_pedigrees(before, after)

    kinds = {c.kind for c in diff.updated[0].field_changes}
    assert kinds == {
        FieldChangeKind.DATE_OF_BIRTH,
        FieldChangeKind.BIOLOGICAL_SEX,
        FieldChangeKind.DEATH_STATUS,
    }


def test_detects_disease_added() -> None:
    disease = DiseaseRecord(disease_id="BRCA1", affection_status="affected", age_at_diagnosis=40)
    before = _pedigree(_individual("a"))
    after = _pedigree(_individual("a", diseases=(disease,)))

    diff = diff_pedigrees(before, after)

    assert len(diff.updated[0].disease_changes) == 1
    assert diff.updated[0].disease_changes[0].added is True
    assert diff.updated[0].disease_changes[0].disease.disease_id == "BRCA1"


def test_detects_disease_removed() -> None:
    disease = DiseaseRecord(disease_id="BRCA1", affection_status="affected", age_at_diagnosis=40)
    before = _pedigree(_individual("a", diseases=(disease,)))
    after = _pedigree(_individual("a"))

    diff = diff_pedigrees(before, after)

    assert diff.updated[0].disease_changes[0].added is False


def test_detects_disease_field_change_as_removed_plus_added() -> None:
    before_disease = DiseaseRecord(
        disease_id="BRCA1",
        affection_status="affected",
        age_at_diagnosis=40,
    )
    after_disease = DiseaseRecord(
        disease_id="BRCA1",
        affection_status="affected",
        age_at_diagnosis=42,
    )
    before = _pedigree(_individual("a", diseases=(before_disease,)))
    after = _pedigree(_individual("a", diseases=(after_disease,)))

    diff = diff_pedigrees(before, after)

    actions = [c.added for c in diff.updated[0].disease_changes]
    assert actions == [False, True]


def test_detects_partner_link_added() -> None:
    link = PartnerLink.of("a", "b")
    before = _pedigree(_individual("a"), _individual("b"))
    after = _pedigree(_individual("a"), _individual("b"), partner_links=frozenset({link}))

    diff = diff_pedigrees(before, after)

    assert len(diff.partner_link_changes) == 1
    assert diff.partner_link_changes[0].added is True


def test_detects_parent_child_link_removed() -> None:
    link = ParentChildLink(parent_id="a", child_id="b")
    before = _pedigree(
        _individual("a"),
        _individual("b"),
        parent_child_links=frozenset({link}),
    )
    after = _pedigree(_individual("a"), _individual("b"))

    diff = diff_pedigrees(before, after)

    assert len(diff.parent_child_link_changes) == 1
    assert diff.parent_child_link_changes[0].added is False


def test_detects_proband_change() -> None:
    before = _pedigree(_individual("a"), proband="a")
    after = _pedigree(_individual("a"), _individual("b"), proband="b")

    diff = diff_pedigrees(before, after)

    assert diff.proband_change is not None
    assert diff.proband_change.before == "a"
    assert diff.proband_change.after == "b"


def test_unchanged_individuals_are_tracked() -> None:
    before = _pedigree(_individual("a", name="Same"))
    after = _pedigree(_individual("a", name="Same"))

    diff = diff_pedigrees(before, after)

    assert len(diff.unchanged) == 1
    assert diff.updated == ()
    assert diff.has_changes() is False


def test_ordering_is_stable_across_multiple_runs() -> None:
    before = _pedigree(_individual("a"), _individual("b"))
    after = _pedigree(
        _individual("a"),
        _individual("b"),
        _individual("c", name="Carol"),
        _individual("d", name="Dave"),
    )

    first = diff_pedigrees(before, after)
    second = diff_pedigrees(before, after)

    assert [a.individual.id for a in first.added] == [a.individual.id for a in second.added]
    assert [a.individual.display_name for a in first.added] == ["Carol", "Dave"]


def test_nested_changes_on_same_individual() -> None:
    """An individual with both a field change and a disease change lands in one entry."""
    disease = DiseaseRecord(disease_id="D", affection_status="affected", age_at_diagnosis=50)
    before = _pedigree(_individual("a", name="Jane"))
    after = _pedigree(_individual("a", name="Jane Smith", diseases=(disease,)))

    diff = diff_pedigrees(before, after)

    assert len(diff.updated) == 1
    assert len(diff.updated[0].field_changes) == 1
    assert len(diff.updated[0].disease_changes) == 1
