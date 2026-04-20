"""Validate a 23andMe raw genotype file and infer biological sex from it.

The file is sent verbatim to Evagene's ``/import/23andme-raw`` endpoint;
this module does *not* reinterpret genotypes or carrier state. Its only
jobs are to check the TSV is well-formed and to derive a ``biological_sex``
value we can record on the individual before import.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_EXPECTED_FIELDS = 4
_Y_CHROMOSOME = "Y"
_NO_CALL = "--"


class BiologicalSex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class GenomeFileError(ValueError):
    """Raised when a 23andMe raw file is missing, empty, or malformed."""


@dataclass(frozen=True)
class GenomeFile:
    path: str
    content: str
    biological_sex: BiologicalSex


def load_genome_file(path: str | Path) -> GenomeFile:
    """Read, validate, and summarise a 23andMe raw genotype TSV.

    Raises :class:`GenomeFileError` if the file is missing, empty, or has
    no recognisable genotype rows. Non-fatal oddities (occasional short
    lines, comments, blank lines) are silently tolerated — 23andMe adds
    header notes that should not fail the import.
    """
    resolved = Path(path)
    try:
        content = resolved.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise GenomeFileError(f"23andMe file not found: {resolved}") from error
    except OSError as error:
        raise GenomeFileError(f"Cannot read 23andMe file {resolved}: {error}") from error

    rows = list(_iter_genotype_rows(content))
    if not rows:
        raise GenomeFileError(
            f"{resolved}: no genotype rows found. Expected a TSV with columns "
            "rsid, chromosome, position, genotype.",
        )

    return GenomeFile(
        path=str(resolved),
        content=content,
        biological_sex=_infer_sex(rows),
    )


@dataclass(frozen=True)
class _Row:
    chromosome: str
    genotype: str


def _iter_genotype_rows(content: str) -> list[_Row]:
    rows: list[_Row] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < _EXPECTED_FIELDS:
            continue
        rows.append(_Row(chromosome=parts[1], genotype=parts[3].strip()))
    return rows


def _infer_sex(rows: list[_Row]) -> BiologicalSex:
    """Male if any Y-chromosome SNP has a real call; female if all are no-calls.

    23andMe reports Y-chromosome SNPs as ``--`` for biological females
    (no Y chromosome present). When a file has no Y-chromosome rows at
    all we cannot tell, and return :data:`BiologicalSex.UNKNOWN`.
    """
    y_rows = [row for row in rows if row.chromosome == _Y_CHROMOSOME]
    if not y_rows:
        return BiologicalSex.UNKNOWN
    if any(row.genotype != _NO_CALL for row in y_rows):
        return BiologicalSex.MALE
    return BiologicalSex.FEMALE
