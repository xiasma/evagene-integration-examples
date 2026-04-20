"""Pure pedigree builder: a mode + shape + seed yield a deterministic blueprint.

The blueprint is transport-agnostic -- each individual carries a
synthetic local id plus the relationship metadata the orchestrator
needs to wire up Evagene calls (which order to make them in, which
existing individual to link to).

Genotypes are decided top-down so the mode's signature is visible at
the root of the tree; the blueprint is then emitted in dependency
order for the ``add-relative`` REST surface, which works bottom-up
(proband exists first, then mother, then father; the server merges
mother + father into the same egg).

"Pure" here is load-bearing for the test suite: fixtures lock in the
expected blueprint for a handful of seeds per mode, and anything that
reaches for ``random.random()`` at module scope would make those tests
flaky.  All randomness flows through the injected :class:`random.Random`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .inheritance import Mode, Sex
from .mode_heuristics import OffspringGenotype, offspring_affected_probability


class Generations(int, Enum):
    THREE = 3
    FOUR = 4


class Size(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class BuildKind(str, Enum):
    """How the orchestrator adds this individual to the pedigree.

    ``PROBAND`` -- created with ``POST /api/individuals`` then attached
    to the pedigree.  Every other kind is built by
    ``POST /api/pedigrees/{id}/register/add-relative`` with the named
    ``relative_type`` and ``relative_of_local_id``.  The server merges
    ``mother`` + ``father`` calls on the same child into a single
    parental egg automatically.
    """

    PROBAND = "proband"
    RELATIVE = "relative"


@dataclass(frozen=True)
class BlueprintIndividual:
    local_id: str
    display_name: str
    sex: Sex
    affected: bool
    carrier: bool
    generation: int
    build_kind: BuildKind
    relative_type: str = ""
    relative_of_local_id: str = ""


@dataclass(frozen=True)
class PedigreeBlueprint:
    individuals: tuple[BlueprintIndividual, ...]
    proband_id: str
    mode: Mode

    def individual(self, local_id: str) -> BlueprintIndividual:
        for ind in self.individuals:
            if ind.local_id == local_id:
                return ind
        raise KeyError(local_id)


_EVEN_SEX_RATIO = 0.5


_SIZE_RANGE: dict[Size, tuple[int, int]] = {
    Size.SMALL: (2, 3),
    Size.MEDIUM: (3, 5),
    Size.LARGE: (5, 7),
}


def build_blueprint(
    mode: Mode,
    generations: Generations,
    size: Size,
    seed: int,
) -> PedigreeBlueprint:
    """Produce a deterministic blueprint -- same inputs give the same pedigree."""
    rng = random.Random(seed)
    plan = _plan_tree(mode, generations, size, rng)
    return _emit_blueprint(plan, mode)


# ---------------------------------------------------------------------------
# Phase 1 -- plan the tree top-down so genotypes inherit correctly.
#
# The tree is a chain of families.  ``root`` is the top: its ``mother``
# and ``father`` are generation-1 founders, and its ``children`` are
# generation 2.  ``root.next_family`` (if present) reuses one of those
# children as the reproducing parent and introduces a married-in
# spouse; its children are generation 3.  And so on.
# ---------------------------------------------------------------------------


@dataclass
class _PlannedPerson:
    key: str
    sex: Sex
    affected: bool
    carrier: bool
    generation: int


@dataclass
class _PlannedFamily:
    mother: _PlannedPerson
    father: _PlannedPerson
    children: list[_PlannedPerson]
    next_family: _PlannedFamily | None = None
    # The child in ``children`` whose family is ``next_family``:
    reproducing_child_key: str = ""


class _KeyGen:
    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> str:
        self._n += 1
        return f"K{self._n:03d}"


@dataclass
class _Plan:
    root: _PlannedFamily
    proband_key: str


def _plan_tree(
    mode: Mode,
    generations: Generations,
    size: Size,
    rng: random.Random,
) -> _Plan:
    next_key = _KeyGen()
    top = _top_founders(mode, next_key)
    root = _plan_family(
        mode=mode,
        size=size,
        rng=rng,
        next_key=next_key,
        mother=top[0],
        father=top[1],
        child_generation=2,
    )

    current = root
    total_generations = int(generations)
    for generation in range(2, total_generations):
        reproducing = _pick_reproducing_child(mode, current.children, rng)
        current.reproducing_child_key = reproducing.key
        spouse = _married_in_spouse(mode, reproducing, next_key)
        mother = reproducing if reproducing.sex is Sex.FEMALE else spouse
        father = reproducing if reproducing.sex is Sex.MALE else spouse
        current.next_family = _plan_family(
            mode=mode,
            size=size,
            rng=rng,
            next_key=next_key,
            mother=mother,
            father=father,
            child_generation=generation + 1,
        )
        current = current.next_family

    proband = _pick_proband(current.children)
    return _Plan(root=root, proband_key=proband.key)


def _top_founders(mode: Mode, next_key: _KeyGen) -> tuple[_PlannedPerson, _PlannedPerson]:
    mother_affected, mother_carrier = _top_founder_status(mode, Sex.FEMALE)
    father_affected, father_carrier = _top_founder_status(mode, Sex.MALE)
    mother = _PlannedPerson(
        key=next_key(),
        sex=Sex.FEMALE,
        affected=mother_affected,
        carrier=mother_carrier,
        generation=1,
    )
    father = _PlannedPerson(
        key=next_key(),
        sex=Sex.MALE,
        affected=father_affected,
        carrier=father_carrier,
        generation=1,
    )
    return (mother, father)


def _married_in_spouse(
    mode: Mode,
    reproducing: _PlannedPerson,
    next_key: _KeyGen,
) -> _PlannedPerson:
    # For teaching AR, the married-in spouse is a silent carrier so
    # that downstream generations can produce an affected proband --
    # the student is then shown the classic "unaffected parents,
    # affected child" signature in a single branch of the tree.
    carrier = mode is Mode.AR
    return _PlannedPerson(
        key=next_key(),
        sex=Sex.MALE if reproducing.sex is Sex.FEMALE else Sex.FEMALE,
        affected=False,
        carrier=carrier,
        generation=reproducing.generation,
    )


def _plan_family(
    *,
    mode: Mode,
    size: Size,
    rng: random.Random,
    next_key: _KeyGen,
    mother: _PlannedPerson,
    father: _PlannedPerson,
    child_generation: int,
) -> _PlannedFamily:
    genotype = OffspringGenotype(
        mother_affected=mother.affected,
        mother_carrier=mother.carrier,
        father_affected=father.affected,
        father_carrier=father.carrier,
    )
    low, high = _SIZE_RANGE[size]
    child_count = rng.randint(low, high)
    children: list[_PlannedPerson] = []
    for _ in range(child_count):
        sex = Sex.FEMALE if rng.random() < _EVEN_SEX_RATIO else Sex.MALE
        affected = rng.random() < offspring_affected_probability(mode, genotype, sex)
        carrier = _is_obligate_carrier(mode, sex, genotype, affected)
        children.append(
            _PlannedPerson(
                key=next_key(),
                sex=sex,
                affected=affected,
                carrier=carrier,
                generation=child_generation,
            )
        )
    return _PlannedFamily(mother=mother, father=father, children=children)


def _pick_reproducing_child(
    mode: Mode,
    children: list[_PlannedPerson],
    rng: random.Random,
) -> _PlannedPerson:
    preferred = _preferred_line_carriers(mode, children)
    pool = preferred or children
    return rng.choice(pool)


def _preferred_line_carriers(
    mode: Mode,
    children: list[_PlannedPerson],
) -> list[_PlannedPerson]:
    if mode is Mode.MT:
        return [c for c in children if c.sex is Sex.FEMALE]
    if mode in (Mode.XLR, Mode.XLD):
        return [c for c in children if c.sex is Sex.FEMALE and (c.affected or c.carrier)]
    if mode is Mode.AD:
        return [c for c in children if c.affected]
    if mode is Mode.AR:
        return [c for c in children if c.affected or c.carrier]
    return []


def _pick_proband(children: list[_PlannedPerson]) -> _PlannedPerson:
    affected = [c for c in children if c.affected]
    if affected:
        return affected[0]
    return children[0]


# ---------------------------------------------------------------------------
# Phase 2 -- emit build steps in dependency order for add-relative.
# ---------------------------------------------------------------------------


def _emit_blueprint(plan: _Plan, mode: Mode) -> PedigreeBlueprint:
    """Walk from the proband upward, producing build steps in order."""
    emitter = _Emitter()
    proband = _find_person(plan.root, plan.proband_key)
    emitter.emit_proband(proband)

    # anchor_key = the key of the child whose parents we add next.
    anchor_key = plan.proband_key
    anchor_family = _find_family_of(plan.root, plan.proband_key)

    while anchor_family is not None:
        anchor_local = emitter.local_id_of(anchor_key)
        emitter.emit_relative(
            person=anchor_family.mother,
            relative_type="mother",
            relative_of_local_id=anchor_local,
        )
        emitter.emit_relative(
            person=anchor_family.father,
            relative_type="father",
            relative_of_local_id=anchor_local,
        )
        for sibling in anchor_family.children:
            if sibling.key == anchor_key:
                continue
            if sibling.key == anchor_family.reproducing_child_key:
                # This child already exists: it will become the
                # next-generation anchor (it was emitted earlier).
                continue
            relative_type = "sister" if sibling.sex is Sex.FEMALE else "brother"
            emitter.emit_relative(
                person=sibling,
                relative_type=relative_type,
                relative_of_local_id=anchor_local,
            )
        # Ascend: the next anchor is the reproducing child of the
        # family one generation up -- i.e. the person whose family we
        # just added parents for is itself a child of the family above.
        parent_family = _parent_family_of(plan.root, anchor_family)
        if parent_family is None:
            break
        anchor_key = parent_family.reproducing_child_key
        anchor_family = parent_family

    return PedigreeBlueprint(
        individuals=tuple(emitter.individuals),
        proband_id=emitter.local_id_of(plan.proband_key),
        mode=mode,
    )


class _Emitter:
    def __init__(self) -> None:
        self.individuals: list[BlueprintIndividual] = []
        self._by_key: dict[str, str] = {}
        self._next_index = 0

    def emit_proband(self, person: _PlannedPerson) -> str:
        return self._emit(person=person, build_kind=BuildKind.PROBAND)

    def emit_relative(
        self,
        *,
        person: _PlannedPerson,
        relative_type: str,
        relative_of_local_id: str,
    ) -> str:
        # Skip if this person was already emitted (the reproducing
        # child of a lower generation is the same _PlannedPerson as
        # the mother/father of the current family).
        existing = self._by_key.get(person.key)
        if existing is not None:
            return existing
        return self._emit(
            person=person,
            build_kind=BuildKind.RELATIVE,
            relative_type=relative_type,
            relative_of_local_id=relative_of_local_id,
        )

    def local_id_of(self, key: str) -> str:
        return self._by_key[key]

    def _emit(
        self,
        *,
        person: _PlannedPerson,
        build_kind: BuildKind,
        relative_type: str = "",
        relative_of_local_id: str = "",
    ) -> str:
        self._next_index += 1
        local_id = f"I{self._next_index:03d}"
        individual = BlueprintIndividual(
            local_id=local_id,
            display_name=f"Person {self._next_index}",
            sex=person.sex,
            affected=person.affected,
            carrier=person.carrier,
            generation=person.generation,
            build_kind=build_kind,
            relative_type=relative_type,
            relative_of_local_id=relative_of_local_id,
        )
        self.individuals.append(individual)
        self._by_key[person.key] = local_id
        return local_id


def _find_person(root: _PlannedFamily, key: str) -> _PlannedPerson:
    family: _PlannedFamily | None = root
    while family is not None:
        if family.mother.key == key:
            return family.mother
        if family.father.key == key:
            return family.father
        for child in family.children:
            if child.key == key:
                return child
        family = family.next_family
    raise KeyError(key)


def _find_family_of(root: _PlannedFamily, child_key: str) -> _PlannedFamily | None:
    family: _PlannedFamily | None = root
    while family is not None:
        for child in family.children:
            if child.key == child_key:
                return family
        family = family.next_family
    return None


def _parent_family_of(
    root: _PlannedFamily,
    family: _PlannedFamily,
) -> _PlannedFamily | None:
    if family is root:
        return None
    current: _PlannedFamily | None = root
    while current is not None:
        if current.next_family is family:
            return current
        current = current.next_family
    return None


def _top_founder_status(mode: Mode, sex: Sex) -> tuple[bool, bool]:
    if mode is Mode.AD:
        return (sex is Sex.FEMALE, False)
    if mode is Mode.AR:
        # Both founders silent carriers -- classic AR pattern.
        return (False, True)
    if mode is Mode.XLR:
        # Carrier mother, unaffected father.
        return (False, sex is Sex.FEMALE)
    if mode is Mode.XLD:
        # Affected father: every daughter affected, no sons affected.
        return (False, False) if sex is Sex.FEMALE else (True, False)
    # Mode.MT
    return (sex is Sex.FEMALE, False)


def _is_obligate_carrier(
    mode: Mode,
    child_sex: Sex,
    parents: OffspringGenotype,
    affected: bool,
) -> bool:
    if affected:
        return False
    if mode is Mode.AR and (
        (parents.mother_affected or parents.mother_carrier)
        and (parents.father_affected or parents.father_carrier)
    ):
        return True
    return (
        mode is Mode.XLR
        and child_sex is Sex.FEMALE
        and (parents.mother_carrier or parents.mother_affected or parents.father_affected)
    )
