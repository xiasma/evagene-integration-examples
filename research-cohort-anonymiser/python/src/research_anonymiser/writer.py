"""Write the anonymised JSON to stdout, a file, or a new Evagene pedigree.

Each output mode is a small :class:`OutputSink` implementation; the app
picks one based on :class:`Config` and never branches again.  Open/closed:
adding a new sink (say, S3) means a new class, not a conditional here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TextIO

from .evagene_client import EvageneApi


class OutputSink(Protocol):
    """A destination for the rendered anonymised JSON document."""

    def emit(self, rendered_json: str, anonymised: dict) -> None: ...  # type: ignore[type-arg]


class StdoutSink:
    """Write the rendered JSON to an injected text sink (usually stdout)."""

    def __init__(self, sink: TextIO) -> None:
        self._sink = sink

    def emit(self, rendered_json: str, anonymised: dict) -> None:  # type: ignore[type-arg]
        del anonymised
        self._sink.write(rendered_json)


class FileSink:
    """Write the rendered JSON to a named file, UTF-8 encoded."""

    def __init__(self, path: Path, confirmation_sink: TextIO) -> None:
        self._path = path
        self._confirmation_sink = confirmation_sink

    def emit(self, rendered_json: str, anonymised: dict) -> None:  # type: ignore[type-arg]
        del anonymised
        self._path.write_text(rendered_json, encoding="utf-8")
        self._confirmation_sink.write(f"wrote {self._path}\n")


class NewPedigreeSink:
    """Create a fresh pedigree on the account and return its ID on stdout.

    Uses the same sequence the intake-form demo does: create pedigree,
    create proband, add-individual-to-pedigree, designate as proband,
    then one ``add-relative`` call per remaining individual in a stable
    breadth-first order.
    """

    def __init__(self, client: EvageneApi, confirmation_sink: TextIO) -> None:
        self._client = client
        self._confirmation_sink = confirmation_sink

    def emit(self, rendered_json: str, anonymised: dict) -> None:  # type: ignore[type-arg]
        del rendered_json
        new_id = self._client.rebuild_pedigree(anonymised)
        self._confirmation_sink.write(f"{new_id}\n")
