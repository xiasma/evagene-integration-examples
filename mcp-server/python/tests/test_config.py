import pytest

from evagene_mcp.config import DEFAULT_BASE_URL, ConfigError, load_config


def test_reads_api_key_and_defaults_base_url() -> None:
    config = load_config({"EVAGENE_API_KEY": "evg_test"})

    assert config.api_key == "evg_test"
    assert config.base_url == DEFAULT_BASE_URL


def test_overrides_base_url_when_set() -> None:
    config = load_config({
        "EVAGENE_API_KEY": "evg_test",
        "EVAGENE_BASE_URL": "http://localhost:8000",
    })

    assert config.base_url == "http://localhost:8000"


def test_rejects_missing_api_key() -> None:
    with pytest.raises(ConfigError):
        load_config({})


def test_rejects_blank_api_key() -> None:
    with pytest.raises(ConfigError):
        load_config({"EVAGENE_API_KEY": "   "})
