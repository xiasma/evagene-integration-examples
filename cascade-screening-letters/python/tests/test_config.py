import pytest

from cascade_letters.config import DEFAULT_BASE_URL, DEFAULT_OUTPUT_DIR, ConfigError, load_config

_VALID_UUID = "11111111-1111-1111-1111-111111111111"
_TEMPLATE_UUID = "22222222-2222-2222-2222-222222222222"


def test_defaults_base_url_and_output_dir() -> None:
    config = load_config(argv=[_VALID_UUID], env={"EVAGENE_API_KEY": "evg_test"})

    assert config.base_url == DEFAULT_BASE_URL
    assert DEFAULT_BASE_URL == "https://evagene.net"
    assert config.output_dir == DEFAULT_OUTPUT_DIR
    assert config.template_id is None
    assert config.dry_run is False


def test_honours_custom_base_url() -> None:
    config = load_config(
        argv=[_VALID_UUID],
        env={"EVAGENE_API_KEY": "evg_test", "EVAGENE_BASE_URL": "https://evagene.example"},
    )

    assert config.base_url == "https://evagene.example"


def test_honours_output_dir_and_template_and_dry_run() -> None:
    config = load_config(
        argv=[
            _VALID_UUID,
            "--output-dir",
            "/tmp/letters",
            "--template",
            _TEMPLATE_UUID,
            "--dry-run",
        ],
        env={"EVAGENE_API_KEY": "evg_test"},
    )

    assert config.output_dir == "/tmp/letters"
    assert config.template_id == _TEMPLATE_UUID
    assert config.dry_run is True


def test_missing_api_key_raises() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config(argv=[_VALID_UUID], env={})


def test_pedigree_id_must_be_uuid() -> None:
    with pytest.raises(ConfigError, match="pedigree-id"):
        load_config(argv=["not-a-uuid"], env={"EVAGENE_API_KEY": "evg_test"})


def test_template_override_must_be_uuid_when_provided() -> None:
    with pytest.raises(ConfigError, match="template"):
        load_config(
            argv=[_VALID_UUID, "--template", "oops"],
            env={"EVAGENE_API_KEY": "evg_test"},
        )
