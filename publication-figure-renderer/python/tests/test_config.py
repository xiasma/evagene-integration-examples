import pytest

from publication_figure_renderer.config import (
    ConfigError,
    LabelStyle,
    load_config,
)

_VALID_UUID = "11111111-1111-1111-1111-111111111111"


def _minimal_env() -> dict[str, str]:
    return {"EVAGENE_API_KEY": "evg_test"}


def test_defaults_to_generation_number_style_without_deidentify() -> None:
    config = load_config([_VALID_UUID, "--output", "fig.svg"], _minimal_env())

    assert config.pedigree_id == _VALID_UUID
    assert config.output_path == "fig.svg"
    assert config.deidentify is False
    assert config.label_style is LabelStyle.GENERATION_NUMBER
    assert config.width is None
    assert config.height is None
    assert config.base_url == "https://evagene.net"


def test_parses_deidentify_and_label_style() -> None:
    config = load_config(
        [_VALID_UUID, "--output", "fig.svg", "--deidentify", "--label-style", "initials"],
        _minimal_env(),
    )
    assert config.deidentify is True
    assert config.label_style is LabelStyle.INITIALS


def test_parses_width_and_height() -> None:
    config = load_config(
        [_VALID_UUID, "--output", "fig.svg", "--width", "800", "--height", "600"],
        _minimal_env(),
    )
    assert config.width == 800
    assert config.height == 600


def test_honours_custom_base_url() -> None:
    config = load_config(
        [_VALID_UUID, "--output", "fig.svg"],
        {"EVAGENE_API_KEY": "evg_test", "EVAGENE_BASE_URL": "https://evagene.example"},
    )
    assert config.base_url == "https://evagene.example"


def test_missing_api_key_raises() -> None:
    with pytest.raises(ConfigError):
        load_config([_VALID_UUID, "--output", "fig.svg"], {})


def test_missing_output_raises() -> None:
    with pytest.raises(ConfigError):
        load_config([_VALID_UUID], _minimal_env())


def test_non_uuid_pedigree_id_raises() -> None:
    with pytest.raises(ConfigError):
        load_config(["not-a-uuid", "--output", "fig.svg"], _minimal_env())


def test_unknown_label_style_raises() -> None:
    with pytest.raises(ConfigError):
        load_config(
            [_VALID_UUID, "--output", "fig.svg", "--label-style", "anagram"],
            _minimal_env(),
        )


def test_non_positive_width_raises() -> None:
    with pytest.raises(ConfigError):
        load_config(
            [_VALID_UUID, "--output", "fig.svg", "--width", "0"],
            _minimal_env(),
        )
