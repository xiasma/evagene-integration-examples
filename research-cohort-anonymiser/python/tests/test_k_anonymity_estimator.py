from typing import Any

from research_anonymiser.k_anonymity_estimator import estimate_k_anonymity


def _individual(sex: str, birth_year: str, diseases: int) -> dict[str, Any]:
    return {
        "biological_sex": sex,
        "events": [{"type": "birth", "date_start": f"{birth_year}-01-01"}],
        "diseases": [
            {"disease_id": f"d{i}", "affection_status": "affected"} for i in range(diseases)
        ],
    }


def test_k_equals_smallest_bucket_size() -> None:
    pedigree = {
        "individuals": [
            _individual("female", "1940", 1),
            _individual("female", "1940", 1),
            _individual("male", "1940", 0),
        ],
    }

    estimate = estimate_k_anonymity(pedigree)

    assert estimate.k == 1
    assert estimate.bucket_count == 2
    assert estimate.smallest_bucket_key == ("male", "1940", 0)


def test_homogeneous_cohort_reports_k_equal_to_cohort_size() -> None:
    pedigree = {
        "individuals": [_individual("female", "1970", 0) for _ in range(5)],
    }

    estimate = estimate_k_anonymity(pedigree)

    assert estimate.k == 5
    assert estimate.bucket_count == 1


def test_empty_pedigree_yields_zero_k() -> None:
    estimate = estimate_k_anonymity({"individuals": []})

    assert estimate.k == 0
    assert estimate.bucket_count == 0
    assert estimate.smallest_bucket_key is None


def test_unknown_birth_year_still_groups() -> None:
    pedigree = {
        "individuals": [
            {"biological_sex": "female", "events": [], "diseases": []},
            {"biological_sex": "female", "events": [], "diseases": []},
        ],
    }

    estimate = estimate_k_anonymity(pedigree)

    assert estimate.k == 2
    assert estimate.smallest_bucket_key == ("female", "unknown", 0)
