"""Load and validate an Evagene v1 ``.xeg`` XML file before upload.

Pure: no network, no logging.  The upload path depends on a guaranteed
well-formed document rooted at ``<Pedigree>``; that invariant belongs
here, not in the HTTP client.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree

_EXPECTED_ROOT = "Pedigree"
_UTF8_BOM = "\ufeff"


class InvalidXegError(ValueError):
    """Raised when a file is not a well-formed Evagene v1 ``.xeg``."""


@dataclass(frozen=True)
class XegDocument:
    raw_text: str


def read_from_file(path: str | Path) -> XegDocument:
    file_path = Path(path)
    if not file_path.is_file():
        raise InvalidXegError(f"file not found: {file_path}")
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidXegError(f"could not read {file_path}: {exc}") from exc
    return parse(text)


def parse(text: str) -> XegDocument:
    stripped = text.removeprefix(_UTF8_BOM)
    try:
        root = etree.fromstring(stripped.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        raise InvalidXegError(
            f"not well-formed XML: {exc.msg} — check the file is a genuine Evagene v1 .xeg"
        ) from exc

    tag = etree.QName(root.tag).localname
    if tag != _EXPECTED_ROOT:
        raise InvalidXegError(
            f"root element is <{tag}>, expected <{_EXPECTED_ROOT}> — "
            "is this an Evagene v1 .xeg file?"
        )
    return XegDocument(raw_text=stripped)
