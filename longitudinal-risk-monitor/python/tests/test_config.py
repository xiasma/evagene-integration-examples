import pytest

from longitudinal_risk_monitor.config import (
    DEFAULT_BASE_URL,
    Channel,
    ConfigError,
    HistoryConfig,
    HistoryFormat,
    RunConfig,
    SeedConfig,
    load_config,
)

_VALID_API_KEY = "evg_test"
_ENV = {"EVAGENE_API_KEY": _VALID_API_KEY}


def test_run_defaults_to_stdout_channel_and_public_base_url() -> None:
    config = load_config(["run"], _ENV)

    assert isinstance(config, RunConfig)
    assert config.channel is Channel.STDOUT
    assert config.channel_arg is None
    assert config.credentials.base_url == DEFAULT_BASE_URL
    assert config.credentials.api_key == _VALID_API_KEY
    assert config.dry_run is False


def test_run_rejects_unknown_channel() -> None:
    with pytest.raises(ConfigError, match="--channel"):
        load_config(["run", "--channel", "email"], _ENV)


def test_run_rejects_file_channel_without_channel_arg() -> None:
    with pytest.raises(ConfigError, match="--channel-arg"):
        load_config(["run", "--channel", "file"], _ENV)


def test_run_rejects_slack_channel_without_channel_arg() -> None:
    with pytest.raises(ConfigError, match="--channel-arg"):
        load_config(["run", "--channel", "slack-webhook"], _ENV)


def test_run_accepts_slack_channel_with_url() -> None:
    config = load_config(
        ["run", "--channel", "slack-webhook", "--channel-arg", "https://hooks.example/T/B/X"],
        _ENV,
    )

    assert isinstance(config, RunConfig)
    assert config.channel is Channel.SLACK_WEBHOOK
    assert config.channel_arg == "https://hooks.example/T/B/X"


def test_run_requires_api_key() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(["run"], {})


def test_seed_requires_api_key() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(["seed"], {})


def test_seed_parses_successfully() -> None:
    config = load_config(["seed"], _ENV)

    assert isinstance(config, SeedConfig)


def test_history_does_not_require_api_key() -> None:
    config = load_config(["history"], {})

    assert isinstance(config, HistoryConfig)
    assert config.pedigree_id is None
    assert config.format is HistoryFormat.TEXT


def test_history_validates_pedigree_uuid() -> None:
    with pytest.raises(ConfigError, match="--pedigree"):
        load_config(["history", "--pedigree", "not-a-uuid"], {})


def test_history_json_format() -> None:
    config = load_config(["history", "--format", "json"], {})

    assert isinstance(config, HistoryConfig)
    assert config.format is HistoryFormat.JSON
