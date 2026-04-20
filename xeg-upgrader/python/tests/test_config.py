from __future__ import annotations

import pytest

from xeg_upgrader.config import DEFAULT_BASE_URL, ConfigError, RunMode, load_config

_INPUT_PATH = "/tmp/legacy-family.xeg"


def test_defaults_mode_to_preview_and_base_url_when_env_unset() -> None:
    config = load_config(argv=[_INPUT_PATH], env={"EVAGENE_API_KEY": "evg_test"})

    assert config.mode is RunMode.PREVIEW
    assert config.base_url == DEFAULT_BASE_URL
    assert DEFAULT_BASE_URL == "https://evagene.net"
    assert config.input_path == _INPUT_PATH


def test_create_flag_selects_create_mode() -> None:
    config = load_config(
        argv=[_INPUT_PATH, "--create"], env={"EVAGENE_API_KEY": "evg_test"}
    )

    assert config.mode is RunMode.CREATE


def test_name_flag_overrides_default_display_name() -> None:
    config = load_config(
        argv=[_INPUT_PATH, "--create", "--name", "Hill family (2019)"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )

    assert config.display_name == "Hill family (2019)"


def test_default_display_name_is_filename_without_extension() -> None:
    config = load_config(argv=[_INPUT_PATH], env={"EVAGENE_API_KEY": "evg_test"})

    assert config.display_name == "legacy-family"


def test_preview_and_create_are_mutually_exclusive() -> None:
    with pytest.raises(ConfigError):
        load_config(
            argv=[_INPUT_PATH, "--preview", "--create"],
            env={"EVAGENE_API_KEY": "evg_test"},
        )


def test_missing_api_key_raises() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(argv=[_INPUT_PATH], env={})


def test_missing_input_path_raises() -> None:
    with pytest.raises(ConfigError):
        load_config(argv=[], env={"EVAGENE_API_KEY": "evg_test"})


def test_honours_custom_base_url() -> None:
    config = load_config(
        argv=[_INPUT_PATH],
        env={
            "EVAGENE_API_KEY": "evg_test",
            "EVAGENE_BASE_URL": "https://evagene.example",
        },
    )

    assert config.base_url == "https://evagene.example"
