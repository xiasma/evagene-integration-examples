"""Write the snippet to a text sink."""

from __future__ import annotations

from typing import TextIO


def present(snippet: str, sink: TextIO) -> None:
    sink.write(snippet)
