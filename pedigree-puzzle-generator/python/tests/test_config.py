"""Tests for CLI + environment parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from pedigree_puzzle.config import ConfigError, load_config
from pedigree_puzzle.inheritance import Mode
from pedigree_puzzle.puzzle_blueprint import Generations, Size


def test_load_config_parses_minimal_valid_inputs() -> None:
    config = load_config(
        argv=["--mode", "AR", "--seed", "42"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )

    assert config.mode is Mode.AR
    assert config.generations is Generations.THREE
    assert config.size is Size.MEDIUM
    assert config.api_key == "evg_test"
    assert config.base_url == "https://evagene.net"
    assert config.output_dir == Path("./puzzles")
    assert config.cleanup is True
    assert config.seed == 42


def test_random_mode_keeps_mode_as_none() -> None:
    config = load_config(argv=[], env={"EVAGENE_API_KEY": "evg_test"})
    assert config.mode is None


def test_no_cleanup_flag_disables_cleanup() -> None:
    config = load_config(
        argv=["--no-cleanup"], env={"EVAGENE_API_KEY": "evg_test"}
    )
    assert config.cleanup is False


def test_missing_api_key_is_usage_error() -> None:
    with pytest.raises(ConfigError):
        load_config(argv=[], env={})


def test_invalid_mode_is_usage_error() -> None:
    with pytest.raises(ConfigError):
        load_config(argv=["--mode", "NOPE"], env={"EVAGENE_API_KEY": "evg_test"})


def test_invalid_generations_is_usage_error() -> None:
    with pytest.raises(ConfigError):
        load_config(
            argv=["--generations", "5"],
            env={"EVAGENE_API_KEY": "evg_test"},
        )


def test_invalid_size_is_usage_error() -> None:
    with pytest.raises(ConfigError):
        load_config(
            argv=["--size", "huge"], env={"EVAGENE_API_KEY": "evg_test"}
        )


def test_base_url_override_from_env() -> None:
    config = load_config(
        argv=[],
        env={"EVAGENE_API_KEY": "evg_test", "EVAGENE_BASE_URL": "http://localhost:8000"},
    )
    assert config.base_url == "http://localhost:8000"
