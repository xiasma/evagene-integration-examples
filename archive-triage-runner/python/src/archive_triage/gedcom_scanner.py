"""Walk a directory and yield ``(path, content)`` pairs for every ``*.ged`` file."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

_GEDCOM_SUFFIX = ".ged"


class ScannerError(ValueError):
    """Raised when the input directory is unusable."""


@dataclass(frozen=True)
class GedcomFile:
    path: Path
    content: str


class GedcomScanner:
    def __init__(self, root: Path) -> None:
        self._root = root

    def scan(self) -> Iterator[GedcomFile]:
        if not self._root.is_dir():
            raise ScannerError(
                f"Input path is not a directory: {self._root} "
                "(pass a folder that contains *.ged files)."
            )
        for path in sorted(self._root.rglob(f"*{_GEDCOM_SUFFIX}")):
            if path.is_file():
                yield GedcomFile(path=path, content=path.read_text(encoding="utf-8"))
