import pytest

from couple_carrier_risk.genome_file import (
    BiologicalSex,
    GenomeFileError,
    load_genome_file,
)
from tests.fixtures_loader import fixture_path


def test_partner_a_fixture_parses_as_male() -> None:
    genome = load_genome_file(fixture_path("partner-a-23andme.txt"))

    assert genome.biological_sex is BiologicalSex.MALE
    assert "rs334" in genome.content


def test_partner_b_fixture_parses_as_female() -> None:
    genome = load_genome_file(fixture_path("partner-b-23andme.txt"))

    assert genome.biological_sex is BiologicalSex.FEMALE


def test_file_without_y_chromosome_rows_is_unknown(tmp_path: object) -> None:
    path = fixture_path("partner-a-23andme.txt").parent / "_scratch_no_y.txt"
    path.write_text(
        "# synthetic\nrs334\t11\t5248232\tAT\n",
        encoding="utf-8",
    )
    try:
        genome = load_genome_file(path)
        assert genome.biological_sex is BiologicalSex.UNKNOWN
    finally:
        path.unlink(missing_ok=True)


def test_missing_file_raises_genome_file_error() -> None:
    with pytest.raises(GenomeFileError, match="not found"):
        load_genome_file("/does/not/exist.txt")


def test_comments_only_raises_genome_file_error(tmp_path: object) -> None:
    path = fixture_path("partner-a-23andme.txt").parent / "_scratch_comments.txt"
    path.write_text("# only comments\n\n", encoding="utf-8")
    try:
        with pytest.raises(GenomeFileError, match="no genotype rows"):
            load_genome_file(path)
    finally:
        path.unlink(missing_ok=True)
