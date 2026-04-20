from datetime import datetime

import pytest

from pedigree_diff.config import (
    DEFAULT_BASE_URL,
    ConfigError,
    OutputFormat,
    load_config,
)

_VALID_UUID = "11111111-1111-1111-1111-111111111111"


def test_two_uuid_args_requires_api_key() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(argv=[_VALID_UUID, _VALID_UUID], env={})


def test_two_file_paths_do_not_require_api_key() -> None:
    config = load_config(argv=["left.json", "right.json"], env={})

    assert config.api_key is None
    assert config.left.path == "left.json"
    assert config.right.path == "right.json"
    assert config.left.pedigree_id is None


def test_mixed_uuid_and_path() -> None:
    config = load_config(
        argv=[_VALID_UUID, "right.json"],
        env={"EVAGENE_API_KEY": "evg_test"},
    )

    assert config.left.pedigree_id == _VALID_UUID
    assert config.right.path == "right.json"


def test_defaults_base_url_when_env_unset() -> None:
    config = load_config(argv=["left.json", "right.json"], env={})

    assert config.base_url == DEFAULT_BASE_URL


def test_format_defaults_to_text() -> None:
    config = load_config(argv=["left.json", "right.json"], env={})

    assert config.output_format is OutputFormat.TEXT


def test_format_accepts_json_and_markdown() -> None:
    json_config = load_config(
        argv=["left.json", "right.json", "--format", "json"],
        env={},
    )
    md_config = load_config(
        argv=["left.json", "right.json", "--format", "markdown"],
        env={},
    )

    assert json_config.output_format is OutputFormat.JSON
    assert md_config.output_format is OutputFormat.MARKDOWN


def test_include_unchanged_flag() -> None:
    config = load_config(
        argv=["left.json", "right.json", "--include-unchanged"],
        env={},
    )

    assert config.include_unchanged is True


def test_since_is_parsed() -> None:
    config = load_config(
        argv=["left.json", "right.json", "--since", "2026-04-15"],
        env={},
    )

    assert config.since == datetime(2026, 4, 15)


def test_since_must_be_iso_8601() -> None:
    with pytest.raises(ConfigError, match="--since"):
        load_config(argv=["left.json", "right.json", "--since", "yesterday"], env={})
