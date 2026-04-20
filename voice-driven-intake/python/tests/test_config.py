from pathlib import Path

import pytest

from voice_driven_intake.config import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_DURATION_S,
    ConfigError,
    load_config,
)


def _full_env() -> dict[str, str]:
    return {
        "OPENAI_API_KEY": "sk-test",
        "ANTHROPIC_API_KEY": "sk-ant-test",
    }


def test_default_flags_require_audio_path_and_both_llm_keys() -> None:
    config = load_config(["recording.wav"], _full_env())

    assert config.audio_path == Path("recording.wav")
    assert config.commit is False
    assert config.show_prompt is False
    assert config.show_transcript is False
    assert config.language is None
    assert config.openai_api_key == "sk-test"
    assert config.anthropic_api_key == "sk-ant-test"
    assert config.evagene_api_key is None
    assert config.evagene_base_url == DEFAULT_BASE_URL
    assert config.max_duration_s == DEFAULT_MAX_DURATION_S


def test_show_prompt_requires_no_keys_and_no_audio() -> None:
    config = load_config(["--show-prompt"], {})

    assert config.show_prompt is True
    assert config.audio_path is None
    assert config.openai_api_key is None
    assert config.anthropic_api_key is None


def test_show_transcript_needs_openai_only() -> None:
    config = load_config(
        ["--show-transcript", "recording.wav"],
        {"OPENAI_API_KEY": "sk-test"},
    )

    assert config.show_transcript is True
    assert config.openai_api_key == "sk-test"
    assert config.anthropic_api_key is None


def test_missing_openai_key_outside_show_prompt() -> None:
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        load_config(["recording.wav"], {"ANTHROPIC_API_KEY": "sk-ant-test"})


def test_missing_anthropic_key_for_extraction() -> None:
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_config(["recording.wav"], {"OPENAI_API_KEY": "sk-test"})


def test_commit_requires_evagene_key() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(["--commit", "recording.wav"], _full_env())


def test_commit_with_evagene_key_populates_everything() -> None:
    env = {**_full_env(), "EVAGENE_API_KEY": "evg_test"}

    config = load_config(["--commit", "recording.wav"], env)

    assert config.commit is True
    assert config.evagene_api_key == "evg_test"


def test_audio_path_is_required_outside_show_prompt() -> None:
    with pytest.raises(ConfigError, match="audio file"):
        load_config([], _full_env())


def test_language_hint_passes_through() -> None:
    config = load_config(["--language", "en", "recording.wav"], _full_env())
    assert config.language == "en"


def test_custom_base_url_and_duration_cap() -> None:
    env = {
        **_full_env(),
        "EVAGENE_BASE_URL": "https://evagene.example",
        "VOICE_INTAKE_MAX_DURATION_S": "60",
    }

    config = load_config(["recording.wav"], env)

    assert config.evagene_base_url == "https://evagene.example"
    assert config.max_duration_s == 60


def test_invalid_duration_cap_raises() -> None:
    with pytest.raises(ConfigError, match="VOICE_INTAKE_MAX_DURATION_S"):
        load_config(
            ["recording.wav"],
            {**_full_env(), "VOICE_INTAKE_MAX_DURATION_S": "not-a-number"},
        )
