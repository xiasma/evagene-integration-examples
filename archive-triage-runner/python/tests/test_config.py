from pathlib import Path

import pytest

from archive_triage.config import DEFAULT_BASE_URL, DEFAULT_CONCURRENCY, ConfigError, load_config


def test_defaults_base_url_and_concurrency_when_env_unset() -> None:
    config = load_config(argv=["archive"], env={"EVAGENE_API_KEY": "evg_test"})

    assert config.base_url == DEFAULT_BASE_URL
    assert DEFAULT_BASE_URL == "https://evagene.net"
    assert config.api_key == "evg_test"
    assert config.input_dir == Path("archive")
    assert config.output_path is None
    assert config.concurrency == DEFAULT_CONCURRENCY


def test_honours_custom_base_url() -> None:
    config = load_config(
        argv=["archive"],
        env={"EVAGENE_API_KEY": "evg_test", "EVAGENE_BASE_URL": "https://evagene.example"},
    )

    assert config.base_url == "https://evagene.example"


def test_output_path_captured_when_provided() -> None:
    config = load_config(
        argv=["archive", "--output", "out.csv"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )

    assert config.output_path == Path("out.csv")


def test_concurrency_captured_when_provided() -> None:
    config = load_config(
        argv=["archive", "--concurrency", "8"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )

    assert config.concurrency == 8


def test_missing_api_key_raises() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(argv=["archive"], env={})


def test_concurrency_must_be_positive() -> None:
    with pytest.raises(ConfigError, match="concurrency"):
        load_config(argv=["archive", "--concurrency", "0"], env={"EVAGENE_API_KEY": "evg_test"})


def test_concurrency_rejects_silly_large_values() -> None:
    with pytest.raises(ConfigError, match="concurrency"):
        load_config(argv=["archive", "--concurrency", "9999"], env={"EVAGENE_API_KEY": "evg_test"})


def test_missing_input_dir_is_usage_error() -> None:
    with pytest.raises(ConfigError):
        load_config(argv=[], env={"EVAGENE_API_KEY": "evg_test"})
