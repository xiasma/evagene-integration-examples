import pytest

from webhook_audit_blotter.config import DEFAULT_PORT, DEFAULT_SQLITE_PATH, ConfigError, load_config


def test_defaults_when_optional_env_unset() -> None:
    config = load_config({"EVAGENE_WEBHOOK_SECRET": "shhh"})

    assert config.port == DEFAULT_PORT
    assert config.sqlite_path == DEFAULT_SQLITE_PATH
    assert config.webhook_secret == "shhh"


def test_missing_secret_raises() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_WEBHOOK_SECRET"):
        load_config({})


def test_invalid_port_raises() -> None:
    with pytest.raises(ConfigError, match="PORT"):
        load_config({"EVAGENE_WEBHOOK_SECRET": "shhh", "PORT": "0"})
    with pytest.raises(ConfigError, match="PORT"):
        load_config({"EVAGENE_WEBHOOK_SECRET": "shhh", "PORT": "999999"})
    with pytest.raises(ConfigError, match="PORT"):
        load_config({"EVAGENE_WEBHOOK_SECRET": "shhh", "PORT": "abc"})


def test_custom_port_and_sqlite_path_honoured() -> None:
    config = load_config(
        {
            "EVAGENE_WEBHOOK_SECRET": "shhh",
            "PORT": "5050",
            "SQLITE_PATH": "/tmp/foo.db",
        },
    )

    assert config.port == 5050
    assert config.sqlite_path == "/tmp/foo.db"
