from pathlib import Path

import pytest

from call_notes_to_pedigree.config import (
    DEFAULT_BASE_URL,
    ConfigError,
    load_config,
)


def test_read_only_default_uses_anthropic_key_only() -> None:
    config = load_config(["transcript.txt"], {"ANTHROPIC_API_KEY": "sk-ant-test"})

    assert config.transcript_path == Path("transcript.txt")
    assert config.commit is False
    assert config.show_prompt is False
    assert config.anthropic_api_key == "sk-ant-test"
    assert config.evagene_api_key is None
    assert config.evagene_base_url == DEFAULT_BASE_URL


def test_stdin_mode_when_no_file_given() -> None:
    config = load_config([], {"ANTHROPIC_API_KEY": "sk-ant-test"})
    assert config.transcript_path is None


def test_commit_requires_evagene_key() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(["--commit"], {"ANTHROPIC_API_KEY": "sk-ant-test"})


def test_commit_with_evagene_key_populates_both() -> None:
    config = load_config(
        ["--commit", "transcript.txt"],
        {"ANTHROPIC_API_KEY": "sk-ant-test", "EVAGENE_API_KEY": "evg_test"},
    )
    assert config.commit is True
    assert config.evagene_api_key == "evg_test"


def test_show_prompt_does_not_require_api_keys() -> None:
    config = load_config(["--show-prompt"], {})

    assert config.show_prompt is True
    assert config.anthropic_api_key is None
    assert config.evagene_api_key is None


def test_missing_anthropic_key_outside_show_prompt() -> None:
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_config([], {})


def test_model_override() -> None:
    config = load_config(
        ["--model", "claude-sonnet-4-5"],
        {"ANTHROPIC_API_KEY": "sk-ant-test"},
    )
    assert config.model == "claude-sonnet-4-5"


def test_custom_base_url() -> None:
    config = load_config(
        [],
        {"ANTHROPIC_API_KEY": "sk-ant-test", "EVAGENE_BASE_URL": "https://evagene.example"},
    )
    assert config.evagene_base_url == "https://evagene.example"
