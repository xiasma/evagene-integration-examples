from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tumour_board_briefing.config import ConfigError, load_config

_PEDIGREE = "11111111-1111-1111-1111-111111111111"
_COUNSELEE = "22222222-2222-2222-2222-222222222222"
_ENV = {"EVAGENE_API_KEY": "evg_test"}
_TODAY = date(2026, 4, 20)


def test_load_config_defaults() -> None:
    config = load_config([_PEDIGREE], _ENV, today=_TODAY)

    assert config.api_key == "evg_test"
    assert config.base_url == "https://evagene.net"
    assert config.pedigree_id == _PEDIGREE
    assert config.counselee_id is None
    assert config.output_path == Path("./tumour-board-11111111-20260420.pdf")
    assert config.models == ("CLAUS", "COUCH", "FRANK", "MANCHESTER", "NICE", "TYRER_CUZICK")


def test_load_config_accepts_counselee_and_output_overrides() -> None:
    config = load_config(
        [_PEDIGREE, "--counselee", _COUNSELEE, "--output", "out.pdf"],
        _ENV,
        today=_TODAY,
    )

    assert config.counselee_id == _COUNSELEE
    assert config.output_path == Path("out.pdf")


def test_load_config_parses_models_list() -> None:
    config = load_config(
        [_PEDIGREE, "--models", "nice,tyrer_cuzick"],
        _ENV,
        today=_TODAY,
    )

    assert config.models == ("NICE", "TYRER_CUZICK")


def test_load_config_rejects_unknown_models() -> None:
    with pytest.raises(ConfigError, match="unsupported"):
        load_config([_PEDIGREE, "--models", "brcapro"], _ENV, today=_TODAY)


def test_load_config_requires_api_key() -> None:
    with pytest.raises(ConfigError, match="EVAGENE_API_KEY"):
        load_config([_PEDIGREE], {}, today=_TODAY)


def test_load_config_rejects_non_uuid_pedigree() -> None:
    with pytest.raises(ConfigError, match="pedigree-id"):
        load_config(["not-a-uuid"], _ENV, today=_TODAY)


def test_load_config_rejects_non_uuid_counselee() -> None:
    with pytest.raises(ConfigError, match="counselee"):
        load_config(
            [_PEDIGREE, "--counselee", "nope"],
            _ENV,
            today=_TODAY,
        )


def test_load_config_deduplicates_models() -> None:
    config = load_config(
        [_PEDIGREE, "--models", "nice,nice,claus"],
        _ENV,
        today=_TODAY,
    )
    assert config.models == ("NICE", "CLAUS")
