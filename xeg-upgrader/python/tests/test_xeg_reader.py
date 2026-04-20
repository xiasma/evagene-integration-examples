from __future__ import annotations

import pytest
from _fixtures import fixture_path, fixture_text

from xeg_upgrader.xeg_reader import InvalidXegError, parse, read_from_file


def test_accepts_well_formed_pedigree_xml() -> None:
    document = parse(fixture_text("sample-simple.xeg"))

    assert "<Pedigree>" in document.raw_text


def test_rejects_malformed_xml_with_parse_error_message() -> None:
    with pytest.raises(InvalidXegError, match="not well-formed XML"):
        parse(fixture_text("malformed.xeg"))


def test_rejects_xml_with_wrong_root_element() -> None:
    foreign = '<?xml version="1.0"?><Family><Individual/></Family>'

    with pytest.raises(InvalidXegError, match=r"<Family>.*<Pedigree>"):
        parse(foreign)


def test_strips_utf8_bom_before_parsing() -> None:
    with_bom = "\ufeff" + '<?xml version="1.0"?><Pedigree/>'

    document = parse(with_bom)

    assert not document.raw_text.startswith("\ufeff")


def test_read_from_file_surfaces_missing_file_as_invalid_xeg() -> None:
    with pytest.raises(InvalidXegError, match="file not found"):
        read_from_file(fixture_path("does-not-exist.xeg"))
