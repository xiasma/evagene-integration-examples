"""Pure transform: SVG text + {old_name -> new_label} -> SVG text.

``lxml.etree`` parses the SVG into a proper node tree so we never touch
attribute strings, never compete with XML escaping rules, and cannot be
fooled by adversarial characters in display names.
"""

from __future__ import annotations

from collections.abc import Mapping

from lxml import etree

_SVG_NS = "http://www.w3.org/2000/svg"
_TEXT_QNAME = f"{{{_SVG_NS}}}text"


class InvalidSvgError(ValueError):
    """Raised when the input cannot be parsed as XML/SVG."""


def deidentify_svg(
    svg_text: str,
    name_to_label: Mapping[str, str],
    *,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """Return the SVG with display names replaced and optional size overrides.

    An empty-string label removes the matching ``<text>`` element entirely,
    so a ``--label-style=off`` pass still produces valid SVG.
    """
    try:
        root = etree.fromstring(svg_text.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        raise InvalidSvgError(f"Could not parse SVG: {exc}") from exc

    _apply_dimensions(root, width, height)
    _apply_label_replacements(root, name_to_label)

    return etree.tostring(root, encoding="unicode")


def _apply_dimensions(
    root: etree._Element,
    width: int | None,
    height: int | None,
) -> None:
    if width is not None:
        root.set("width", str(width))
    if height is not None:
        root.set("height", str(height))


def _apply_label_replacements(
    root: etree._Element,
    name_to_label: Mapping[str, str],
) -> None:
    if not name_to_label:
        return
    # iter() with a namespaced qname is both typed cleanly and avoids any
    # xpath-string quoting concerns around adversarial input.
    for node in list(root.iter(_TEXT_QNAME)):
        current = _full_text(node)
        if current not in name_to_label:
            continue
        replacement = name_to_label[current]
        if replacement == "":
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
        else:
            _set_text(node, replacement)


def _full_text(node: etree._Element) -> str:
    """Return the text content of a <text> node, including any <tspan> children."""
    parts: list[str] = []
    if node.text is not None:
        parts.append(node.text)
    for child in node:
        parts.append(_full_text(child))
        if child.tail is not None:
            parts.append(child.tail)
    return "".join(parts)


def _set_text(node: etree._Element, replacement: str) -> None:
    # Clear any child <tspan> nodes so the replacement does not concatenate
    # with stale text.  lxml escapes the replacement automatically on
    # serialisation -- we never build XML by string concatenation.
    for child in list(node):
        node.remove(child)
    node.text = replacement
