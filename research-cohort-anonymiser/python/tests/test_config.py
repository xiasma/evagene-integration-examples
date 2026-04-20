import pytest

from research_anonymiser.config import (
    DEFAULT_BASE_URL,
    AgePrecision,
    ConfigError,
    load_config,
)

_VALID_UUID = "11111111-1111-1111-1111-111111111111"


def test_defaults_base_url_and_year_precision_and_keep_sex() -> None:
    config = load_config(argv=[_VALID_UUID], env={"EVAGENE_API_KEY": "evg_test"})

    assert config.base_url == DEFAULT_BASE_URL
    assert config.api_key == "evg_test"
    assert config.pedigree_id == _VALID_UUID
    assert config.output_path is None
    assert config.as_new_pedigree is False
    assert config.age_precision is AgePrecision.YEAR
    assert config.keep_sex is True


def test_honours_custom_base_url() -> None:
    config = load_config(
        argv=[_VALID_UUID],
        env={"EVAGENE_API_KEY": "evg_test", "EVAGENE_BASE_URL": "https://evagene.example"},
    )
    assert config.base_url == "https://evagene.example"


def test_missing_api_key_raises() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(argv=[_VALID_UUID], env={})


def test_pedigree_id_must_be_uuid() -> None:
    with pytest.raises(ConfigError, match="pedigree-id"):
        load_config(argv=["not-a-uuid"], env={"EVAGENE_API_KEY": "evg_test"})


def test_output_and_as_new_pedigree_are_mutually_exclusive() -> None:
    with pytest.raises(ConfigError, match="mutually exclusive"):
        load_config(
            argv=[_VALID_UUID, "--output", "out.json", "--as-new-pedigree"],
            env={"EVAGENE_API_KEY": "evg_test"},
        )


def test_parses_decade_precision() -> None:
    config = load_config(
        argv=[_VALID_UUID, "--age-precision", "decade"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )
    assert config.age_precision is AgePrecision.DECADE


def test_parses_five_year_precision() -> None:
    config = load_config(
        argv=[_VALID_UUID, "--age-precision", "five-year"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )
    assert config.age_precision is AgePrecision.FIVE_YEAR


def test_no_keep_sex_flips_the_flag() -> None:
    config = load_config(
        argv=[_VALID_UUID, "--no-keep-sex"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )
    assert config.keep_sex is False
