import pytest

from couple_carrier_risk.config import (
    AUTO_ANCESTRY,
    DEFAULT_BASE_URL,
    ConfigError,
    load_config,
)


def _env() -> dict[str, str]:
    return {"EVAGENE_API_KEY": "evg_test"}


def _minimal_argv(*extra: str) -> list[str]:
    return [
        "--partner-a", "a.txt",
        "--partner-b", "b.txt",
        *extra,
    ]


def test_defaults_base_url_format_cleanup_and_auto_ancestry() -> None:
    config = load_config(_minimal_argv(), _env())

    assert config.base_url == DEFAULT_BASE_URL
    assert DEFAULT_BASE_URL == "https://evagene.net"
    assert config.partner_a_file == "a.txt"
    assert config.partner_b_file == "b.txt"
    assert config.ancestry_a == AUTO_ANCESTRY
    assert config.ancestry_b == AUTO_ANCESTRY
    assert config.output_format == "table"
    assert config.cleanup is True


def test_honours_custom_base_url() -> None:
    config = load_config(
        _minimal_argv(),
        {"EVAGENE_API_KEY": "evg_test", "EVAGENE_BASE_URL": "https://evagene.example"},
    )

    assert config.base_url == "https://evagene.example"


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_accepts_supported_output_formats(fmt: str) -> None:
    config = load_config(_minimal_argv("--output", fmt), _env())

    assert config.output_format == fmt


def test_rejects_unknown_output_format() -> None:
    with pytest.raises(ConfigError):
        load_config(_minimal_argv("--output", "yaml"), _env())


def test_no_cleanup_overrides_default() -> None:
    config = load_config(_minimal_argv("--no-cleanup"), _env())

    assert config.cleanup is False


def test_carries_ancestry_flags() -> None:
    config = load_config(
        _minimal_argv("--ancestry-a", "ashkenazi_jewish", "--ancestry-b", "mediterranean"),
        _env(),
    )

    assert config.ancestry_a == "ashkenazi_jewish"
    assert config.ancestry_b == "mediterranean"


def test_missing_api_key_raises() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(_minimal_argv(), {})


def test_partner_files_are_required() -> None:
    with pytest.raises(ConfigError):
        load_config(["--partner-a", "a.txt"], _env())
