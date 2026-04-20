"""End-to-end workflow: upload two partners, fetch risks, combine, clean up.

The orchestrator owns the lifetime of the scratch pedigree and
individuals. Cleanup runs in a ``finally`` block so a half-built
workspace never lingers on the user's account, even when an import
fails mid-run.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO

from .config import AUTO_ANCESTRY, Config
from .couple_risk_calculator import (
    CoupleRow,
    PartnerRisks,
    build_couple_rows,
    parse_population_risks,
)
from .evagene_client import EvageneClient, Individual
from .genome_file import BiologicalSex, GenomeFile, load_genome_file
from .presenters import presenter_for

SCRATCH_PEDIGREE_NAME = "couple-carrier-risk scratch"


@dataclass(frozen=True)
class PartnerInputs:
    display_name: str
    genome: GenomeFile
    ancestry: str


def run_couple_screening(
    config: Config,
    client: EvageneClient,
    sink: TextIO,
) -> None:
    """Create scratch workspace, upload both partners, compute, render, clean up."""
    partner_a, partner_b = _load_partners(config)
    pedigree_id = client.create_pedigree(SCRATCH_PEDIGREE_NAME)
    created_individuals: list[Individual] = []

    try:
        rows = _screen_couple(
            client=client,
            pedigree_id=pedigree_id,
            partners=(partner_a, partner_b),
            created_individuals=created_individuals,
        )
        presenter_for(config.output_format)(rows, sink)
    finally:
        if config.cleanup:
            _cleanup(client, pedigree_id, created_individuals)


def _load_partners(config: Config) -> tuple[PartnerInputs, PartnerInputs]:
    return (
        PartnerInputs(
            display_name="Partner A",
            genome=load_genome_file(config.partner_a_file),
            ancestry=config.ancestry_a,
        ),
        PartnerInputs(
            display_name="Partner B",
            genome=load_genome_file(config.partner_b_file),
            ancestry=config.ancestry_b,
        ),
    )


def _screen_couple(
    *,
    client: EvageneClient,
    pedigree_id: str,
    partners: tuple[PartnerInputs, PartnerInputs],
    created_individuals: list[Individual],
) -> tuple[CoupleRow, ...]:
    risks = []
    for partner in partners:
        individual = _onboard_partner(client, pedigree_id, partner)
        created_individuals.append(individual)
        payload = client.get_population_risks(individual.id)
        risks.append(
            PartnerRisks(
                biological_sex=partner.genome.biological_sex,
                risks=parse_population_risks(payload),
            ),
        )
    return build_couple_rows(risks[0], risks[1])


def _onboard_partner(
    client: EvageneClient,
    pedigree_id: str,
    partner: PartnerInputs,
) -> Individual:
    """Create the individual, attach to the pedigree, record ancestry, import genome."""
    individual = client.create_individual(
        display_name=partner.display_name,
        biological_sex=partner.genome.biological_sex,
    )
    client.add_individual_to_pedigree(pedigree_id, individual.id)
    _record_ancestry_if_explicit(client, individual.id, partner.ancestry)
    client.import_23andme_raw(
        pedigree_id=pedigree_id,
        individual_id=individual.id,
        tsv=partner.genome.content,
    )
    return individual


def _record_ancestry_if_explicit(
    client: EvageneClient,
    individual_id: str,
    ancestry: str,
) -> None:
    """Attach the named ancestry (proportion 1.0) when the caller specifies one.

    ``AUTO_ANCESTRY`` ("auto") defers to Evagene's own ancestry inference.
    An unknown population key surfaces as an error — silent fallback would
    hide a typo that produces subtly wrong carrier frequencies.
    """
    if ancestry == AUTO_ANCESTRY:
        return
    ancestry_id = client.find_ancestry_id_by_population_key(ancestry)
    if ancestry_id is None:
        raise AncestryNotFoundError(
            f"No ancestry in the Evagene catalogue has population_key={ancestry!r}. "
            "List available keys at GET /api/ancestries or pass --ancestry-a auto.",
        )
    client.add_ancestry_to_individual(individual_id=individual_id, ancestry_id=ancestry_id)


class AncestryNotFoundError(LookupError):
    """Raised when a CLI-supplied ancestry key has no match in the catalogue."""


def _cleanup(
    client: EvageneClient,
    pedigree_id: str,
    created_individuals: list[Individual],
) -> None:
    """Best-effort teardown: never mask the original error."""
    for individual in created_individuals:
        _swallow(client.delete_individual, individual.id)
    _swallow(client.delete_pedigree, pedigree_id)


def _swallow(thunk: Callable[[str], None], argument: str) -> None:
    # Cleanup must never raise — a teardown error would mask the caller's original failure.
    with contextlib.suppress(Exception):
        thunk(argument)


# Keep the biological-sex symbol in scope for callers that want to
# branch on ``PartnerInputs.genome.biological_sex`` without importing
# the genome module directly.
__all__ = [
    "BiologicalSex",
    "PartnerInputs",
    "SCRATCH_PEDIGREE_NAME",
    "run_couple_screening",
]
