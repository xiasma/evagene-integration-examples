import pytest

from notebook_explorer.config import DEFAULT_BASE_URL, ConfigError, load_config


def test_requires_api_key() -> None:
    with pytest.raises(ConfigError):
        load_config({})


def test_defaults_base_url_to_public_host() -> None:
    config = load_config({"EVAGENE_API_KEY": "evg_test"})
    assert config.base_url == DEFAULT_BASE_URL
    assert config.api_key == "evg_test"


def test_honours_base_url_override_and_strips_trailing_slash() -> None:
    config = load_config(
        {"EVAGENE_API_KEY": "evg_test", "EVAGENE_BASE_URL": "https://evagene.example/"}
    )
    assert config.base_url == "https://evagene.example"
