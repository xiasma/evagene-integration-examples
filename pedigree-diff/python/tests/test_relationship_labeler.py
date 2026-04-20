from pedigree_diff.relationship_labeler import label_relationship
from pedigree_diff.snapshot import (
    IndividualSnapshot,
    ParentChildLink,
    PartnerLink,
    PedigreeSnapshot,
)


def _ind(ind_id: str, sex: str) -> IndividualSnapshot:
    return IndividualSnapshot(
        id=ind_id,
        display_name=ind_id,
        biological_sex=sex,
        date_of_birth=None,
        death_status="alive",
        diseases=(),
        is_proband=False,
    )


def _family() -> PedigreeSnapshot:
    # pgf + pgm -> father -> proband; mgf + mgm -> mother -> proband.
    individuals = (
        _ind("pgf", "male"),
        _ind("pgm", "female"),
        _ind("mgf", "male"),
        _ind("mgm", "female"),
        _ind("father", "male"),
        _ind("mother", "female"),
        _ind("uncle", "male"),
        _ind("aunt", "female"),
        _ind("cousin", "female"),
        _ind("sibling", "male"),
        _ind("proband", "female"),
        _ind("child", "male"),
        _ind("grandchild", "female"),
        _ind("husband", "male"),
    )
    partners = frozenset(
        {
            PartnerLink.of("pgf", "pgm"),
            PartnerLink.of("mgf", "mgm"),
            PartnerLink.of("father", "mother"),
            PartnerLink.of("aunt", "uncle"),
            PartnerLink.of("proband", "husband"),
        },
    )
    parents = frozenset(
        {
            ParentChildLink("pgf", "father"),
            ParentChildLink("pgm", "father"),
            ParentChildLink("pgf", "uncle"),
            ParentChildLink("pgm", "uncle"),
            ParentChildLink("mgf", "mother"),
            ParentChildLink("mgm", "mother"),
            ParentChildLink("mgf", "aunt"),
            ParentChildLink("mgm", "aunt"),
            ParentChildLink("father", "proband"),
            ParentChildLink("mother", "proband"),
            ParentChildLink("father", "sibling"),
            ParentChildLink("mother", "sibling"),
            ParentChildLink("aunt", "cousin"),
            ParentChildLink("proband", "child"),
            ParentChildLink("child", "grandchild"),
        },
    )
    return PedigreeSnapshot(
        pedigree_id="p",
        display_name="Family",
        proband_id="proband",
        individuals=individuals,
        partner_links=partners,
        parent_child_links=parents,
    )


def test_proband_labels_as_proband() -> None:
    assert label_relationship(_family(), "proband") == "proband"


def test_mother_and_father() -> None:
    family = _family()
    assert label_relationship(family, "mother") == "mother"
    assert label_relationship(family, "father") == "father"


def test_paternal_and_maternal_grandparents() -> None:
    family = _family()
    assert label_relationship(family, "pgf") == "paternal grandfather"
    assert label_relationship(family, "pgm") == "paternal grandmother"
    assert label_relationship(family, "mgf") == "maternal grandfather"
    assert label_relationship(family, "mgm") == "maternal grandmother"


def test_siblings_and_aunt_uncle() -> None:
    family = _family()
    assert label_relationship(family, "sibling") == "brother"
    assert label_relationship(family, "aunt") == "maternal aunt"
    assert label_relationship(family, "uncle") == "paternal uncle"


def test_first_cousin() -> None:
    assert label_relationship(_family(), "cousin") == "first cousin"


def test_child_and_grandchild() -> None:
    family = _family()
    assert label_relationship(family, "child") == "son"
    assert label_relationship(family, "grandchild") == "granddaughter"


def test_partner() -> None:
    assert label_relationship(_family(), "husband") == "husband"


def test_unknown_individual_falls_back_to_relative() -> None:
    family = _family()
    assert label_relationship(family, "nobody") == "relative"


def test_no_proband_falls_back_to_relative() -> None:
    family = _family()
    no_proband = PedigreeSnapshot(
        pedigree_id=family.pedigree_id,
        display_name=family.display_name,
        proband_id=None,
        individuals=family.individuals,
        partner_links=family.partner_links,
        parent_child_links=family.parent_child_links,
    )
    assert label_relationship(no_proband, "mother") == "relative"
