import pytest

from nice_traffic_light.config import DEFAULT_BASE_URL, ConfigError, load_config

_VALID_UUID = "11111111-1111-1111-1111-111111111111"


def test_defaults_base_url_when_env_unset() -> None:
    config = load_config(argv=[_VALID_UUID], env={"EVAGENE_API_KEY": "evg_test"})

    assert config.base_url == DEFAULT_BASE_URL
    assert DEFAULT_BASE_URL == "https://evagene.net"
    assert config.api_key == "evg_test"
    assert config.pedigree_id == _VALID_UUID
    assert config.counselee_id is None


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


def test_counselee_must_be_uuid_when_provided() -> None:
    with pytest.raises(ConfigError, match="counselee"):
        load_config(
            argv=[_VALID_UUID, "--counselee", "oops"],
            env={"EVAGENE_API_KEY": "evg_test"},
        )
