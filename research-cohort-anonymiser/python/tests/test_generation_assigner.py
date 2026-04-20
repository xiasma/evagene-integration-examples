from typing import Any

from research_anonymiser.generation_assigner import assign_generation_labels


def _basic_pedigree() -> dict[str, Any]:
    """Three-generation autosomal-dominant family: two grandparents, one child, one grandchild."""
    return {
        "individuals": [
            {"id": "gf"},
            {"id": "gm"},
            {"id": "parent"},
            {"id": "spouse"},
            {"id": "child"},
        ],
        "relationships": [
            {"id": "r-gp", "members": ["gf", "gm"]},
            {"id": "r-parents", "members": ["parent", "spouse"]},
        ],
        "eggs": [
            {"id": "e1", "individual_id": "parent", "relationship_id": "r-gp"},
            {"id": "e2", "individual_id": "child", "relationship_id": "r-parents"},
        ],
    }


def test_founders_are_generation_one() -> None:
    labels = assign_generation_labels(_basic_pedigree())

    assert labels["gf"] == "I"
    assert labels["gm"] == "I"


def test_children_and_grandchildren_get_successive_roman_numerals() -> None:
    labels = assign_generation_labels(_basic_pedigree())

    assert labels["parent"] == "II"
    assert labels["child"] == "III"


def test_spouse_with_no_parents_is_aligned_to_partner_generation() -> None:
    labels = assign_generation_labels(_basic_pedigree())

    assert labels["spouse"] == "II"


def test_consanguineous_family_still_yields_stable_labels() -> None:
    """First-cousin marriage: the child's two parents are both generation II."""
    pedigree: dict[str, Any] = {
        "individuals": [
            {"id": "gf1"},
            {"id": "gm1"},
            {"id": "gf2"},
            {"id": "gm2"},
            {"id": "parentA"},
            {"id": "parentB"},
            {"id": "child"},
        ],
        "relationships": [
            {"id": "gp1", "members": ["gf1", "gm1"]},
            {"id": "gp2", "members": ["gf2", "gm2"]},
            {"id": "pr", "members": ["parentA", "parentB"], "consanguinity": 0.0625},
        ],
        "eggs": [
            {"id": "e1", "individual_id": "parentA", "relationship_id": "gp1"},
            {"id": "e2", "individual_id": "parentB", "relationship_id": "gp2"},
            {"id": "e3", "individual_id": "child", "relationship_id": "pr"},
        ],
    }

    labels = assign_generation_labels(pedigree)

    assert labels["gf1"] == labels["gm1"] == "I"
    assert labels["gf2"] == labels["gm2"] == "I"
    assert labels["parentA"] == "II"
    assert labels["parentB"] == "II"
    assert labels["child"] == "III"


def test_individual_with_unresolvable_parent_falls_back_to_unknown_label() -> None:
    """An individual whose only parent is a ghost we never declared cannot be
    placed; the fallback label keeps downstream code from exploding."""
    pedigree: dict[str, Any] = {
        "individuals": [{"id": "ghost_child"}],
        "relationships": [
            {"id": "r-ghost", "members": ["phantom"]},
        ],
        "eggs": [
            {"id": "e", "individual_id": "ghost_child", "relationship_id": "r-ghost"},
        ],
    }

    labels = assign_generation_labels(pedigree)

    assert labels["ghost_child"] == "G?"
