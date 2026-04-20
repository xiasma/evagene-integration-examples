import json
from pathlib import Path
from typing import Any

import pytest
from lxml import etree

from publication_figure_renderer.config import LabelStyle
from publication_figure_renderer.label_mapper import build_label_mapping
from publication_figure_renderer.svg_deidentifier import (
    InvalidSvgError,
    deidentify_svg,
)

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_SVG_NS = "http://www.w3.org/2000/svg"


def _sample_svg() -> str:
    return (_FIXTURES / "sample.svg").read_text(encoding="utf-8")


def _expected_deidentified_svg() -> str:
    return (_FIXTURES / "deidentified.svg").read_text(encoding="utf-8")


def _sample_detail() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (_FIXTURES / "sample-detail.json").read_text(encoding="utf-8")
    )
    return payload


def _generation_mapping() -> dict[str, str]:
    detail = _sample_detail()
    id_to_label = build_label_mapping(detail, LabelStyle.GENERATION_NUMBER)
    individuals = detail["individuals"]
    return {ind["display_name"]: id_to_label[ind["id"]] for ind in individuals}


def _text_of(node: etree._Element) -> str:
    parts: list[str] = []
    if node.text is not None:
        parts.append(node.text)
    for child in node:
        parts.append(_text_of(child))
        if child.tail is not None:
            parts.append(child.tail)
    return "".join(parts)


def _text_contents(svg_text: str) -> list[str]:
    root = etree.fromstring(svg_text.encode("utf-8"))
    return [_text_of(t) for t in root.iter(f"{{{_SVG_NS}}}text")]


def _attribute_snapshot(svg_text: str, local_name: str) -> list[dict[str, str]]:
    root = etree.fromstring(svg_text.encode("utf-8"))
    return [_attrs_as_dict(node) for node in root.iter(f"{{{_SVG_NS}}}{local_name}")]


def _attrs_as_dict(node: etree._Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in node.attrib.items():
        out[str(key)] = str(value)
    return out


def test_display_names_disappear_when_replaced_with_generation_number_labels() -> None:
    rendered = deidentify_svg(_sample_svg(), _generation_mapping())

    for name in (
        "Robert Smith",
        "Mary Smith",
        "David Smith",
        "Linda <O'Brien> & Co",
        "Sarah Smith",
    ):
        assert name not in rendered

    assert sorted(_text_contents(rendered)) == sorted(
        ["I-1", "I-2", "II-1", "II-2", "III-1"]
    )


def test_non_text_attributes_are_preserved_structurally() -> None:
    rendered = deidentify_svg(_sample_svg(), _generation_mapping())

    for name in ("rect", "circle", "polygon", "line"):
        assert _attribute_snapshot(rendered, name) == _attribute_snapshot(
            _sample_svg(), name
        ), name


def test_names_containing_xml_special_characters_are_handled_safely() -> None:
    rendered = deidentify_svg(_sample_svg(), {"Linda <O'Brien> & Co": "II-2"})

    assert "II-2" in rendered
    assert "Linda" not in rendered
    # Round-trip still parses as XML.
    etree.fromstring(rendered.encode("utf-8"))


def test_a_label_with_injection_shaped_characters_is_text_escaped_on_output() -> None:
    rendered = deidentify_svg(_sample_svg(), {"Robert Smith": "<script>alert(1)</script>"})

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    etree.fromstring(rendered.encode("utf-8"))


def test_empty_string_label_removes_the_matching_text_element() -> None:
    rendered = deidentify_svg(_sample_svg(), {"Sarah Smith": ""})

    contents = _text_contents(rendered)
    assert "Sarah Smith" not in contents
    assert "Robert Smith" in contents
    assert "Mary Smith" in contents


def test_width_and_height_overrides_update_root_only() -> None:
    rendered = deidentify_svg(_sample_svg(), {}, width=1024, height=768)

    root = etree.fromstring(rendered.encode("utf-8"))
    assert root.get("width") == "1024"
    assert root.get("height") == "768"
    original = etree.fromstring(_sample_svg().encode("utf-8"))
    assert root.get("viewBox") == original.get("viewBox")


def test_matches_the_canonical_deidentified_fixture_structurally() -> None:
    rendered = deidentify_svg(_sample_svg(), _generation_mapping())

    assert sorted(_text_contents(rendered)) == sorted(
        _text_contents(_expected_deidentified_svg())
    )
    rendered_root = etree.fromstring(rendered.encode("utf-8"))
    expected_root = etree.fromstring(_expected_deidentified_svg().encode("utf-8"))
    assert len(list(rendered_root.iter())) == len(list(expected_root.iter()))


def test_malformed_svg_raises_invalid_svg_error() -> None:
    with pytest.raises(InvalidSvgError):
        deidentify_svg("<svg><text>broken", {})
