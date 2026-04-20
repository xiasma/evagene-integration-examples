"""Tests for the pure pedigree-blueprint builder."""

from __future__ import annotations

from pedigree_puzzle.inheritance import Mode, Sex
from pedigree_puzzle.puzzle_blueprint import (
    BlueprintIndividual,
    BuildKind,
    Generations,
    PedigreeBlueprint,
    Size,
    build_blueprint,
)

_FIXED_SEEDS = (1, 42, 137, 2718, 9000)


def test_blueprint_is_deterministic_from_seed() -> None:
    for mode in Mode:
        for seed in _FIXED_SEEDS:
            first = build_blueprint(mode, Generations.THREE, Size.MEDIUM, seed)
            second = build_blueprint(mode, Generations.THREE, Size.MEDIUM, seed)
            assert first == second, f"Non-deterministic blueprint for {mode.value} seed={seed}"


def test_different_seeds_give_different_blueprints() -> None:
    first = build_blueprint(Mode.AD, Generations.THREE, Size.MEDIUM, 1)
    second = build_blueprint(Mode.AD, Generations.THREE, Size.MEDIUM, 2)
    assert first != second


def test_every_non_proband_names_an_existing_local_id_as_relative() -> None:
    for mode in Mode:
        for seed in _FIXED_SEEDS:
            blueprint = build_blueprint(mode, Generations.THREE, Size.MEDIUM, seed)
            known_ids = {ind.local_id for ind in blueprint.individuals}
            for ind in blueprint.individuals:
                if ind.build_kind is BuildKind.PROBAND:
                    continue
                assert ind.relative_type, f"{ind.local_id} has no relative_type"
                assert ind.relative_of_local_id in known_ids, (
                    f"{ind.local_id} names unknown relative {ind.relative_of_local_id!r}"
                )


def test_blueprint_has_exactly_one_proband() -> None:
    blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.MEDIUM, 1)
    probands = [i for i in blueprint.individuals if i.build_kind is BuildKind.PROBAND]
    assert len(probands) == 1
    assert probands[0].local_id == blueprint.proband_id


def test_ad_mode_has_affected_individuals_across_multiple_generations() -> None:
    # Vertical transmission is the defining AD cue.
    for seed in _FIXED_SEEDS:
        blueprint = build_blueprint(Mode.AD, Generations.THREE, Size.MEDIUM, seed)
        affected_generations = {i.generation for i in blueprint.individuals if i.affected}
        assert len(affected_generations) >= 2, (
            f"AD seed={seed} expected affected individuals in >=2 generations, "
            f"got {affected_generations}"
        )


def test_xlr_mode_only_affects_males() -> None:
    for seed in _FIXED_SEEDS:
        blueprint = build_blueprint(Mode.XLR, Generations.THREE, Size.MEDIUM, seed)
        affected_females = [
            i for i in blueprint.individuals if i.affected and i.sex is Sex.FEMALE
        ]
        assert affected_females == [], (
            f"XLR seed={seed} produced an affected female: {affected_females}"
        )


def test_mt_mode_affected_child_always_has_affected_mother() -> None:
    for seed in _FIXED_SEEDS:
        blueprint = build_blueprint(Mode.MT, Generations.THREE, Size.MEDIUM, seed)
        # In MT, any affected child must have an affected mother (not father).
        for child in blueprint.individuals:
            if not child.affected or child.build_kind is BuildKind.PROBAND:
                continue
            mother = _mother_of(blueprint, child)
            if mother is not None:
                assert mother.affected, (
                    f"MT seed={seed}: {child.local_id} is affected "
                    f"but mother {mother.local_id} is not"
                )


def test_ar_mode_affected_children_have_at_least_one_known_allele_source() -> None:
    for seed in _FIXED_SEEDS:
        blueprint = build_blueprint(Mode.AR, Generations.THREE, Size.MEDIUM, seed)
        for child in blueprint.individuals:
            if not child.affected:
                continue
            parents = _parents_of(blueprint, child)
            if len(parents) < 2:
                continue  # proband (emitted first, parents attached later)
            for parent in parents:
                assert parent.affected or parent.carrier, (
                    f"AR seed={seed}: affected {child.local_id} has "
                    f"non-carrier parent {parent.local_id}"
                )


def test_size_small_produces_smaller_pedigrees_than_large() -> None:
    small = build_blueprint(Mode.AD, Generations.THREE, Size.SMALL, 123)
    large = build_blueprint(Mode.AD, Generations.THREE, Size.LARGE, 123)
    assert len(small.individuals) < len(large.individuals)


def test_generations_four_produces_more_individuals_than_three() -> None:
    three = build_blueprint(Mode.AD, Generations.THREE, Size.MEDIUM, 99)
    four = build_blueprint(Mode.AD, Generations.FOUR, Size.MEDIUM, 99)
    assert len(four.individuals) > len(three.individuals)


def test_blueprint_order_respects_add_relative_dependencies() -> None:
    # The orchestrator walks the blueprint in order; every relative's
    # anchor must already have appeared by that point.
    blueprint = build_blueprint(Mode.XLD, Generations.FOUR, Size.MEDIUM, 55)
    seen: set[str] = set()
    for ind in blueprint.individuals:
        if ind.build_kind is BuildKind.PROBAND:
            seen.add(ind.local_id)
            continue
        assert ind.relative_of_local_id in seen, (
            f"{ind.local_id} emitted before its anchor {ind.relative_of_local_id!r}"
        )
        seen.add(ind.local_id)


def _mother_of(
    blueprint: PedigreeBlueprint,
    child: BlueprintIndividual,
) -> BlueprintIndividual | None:
    for candidate in blueprint.individuals:
        if (
            candidate.relative_type == "mother"
            and candidate.relative_of_local_id == child.local_id
        ):
            return candidate
    return None


def _parents_of(
    blueprint: PedigreeBlueprint,
    child: BlueprintIndividual,
) -> list[BlueprintIndividual]:
    parents: list[BlueprintIndividual] = []
    for candidate in blueprint.individuals:
        if candidate.relative_of_local_id != child.local_id:
            continue
        if candidate.relative_type in ("mother", "father"):
            parents.append(candidate)
    return parents
