"""Writes an SVG document to a file on disk.

Isolating this keeps the rest of the pipeline testable without touching
the filesystem.
"""

from __future__ import annotations

from pathlib import Path


def write_svg(svg_text: str, path: str | Path) -> Path:
    """Write ``svg_text`` to ``path`` as UTF-8.  Returns the path for chaining."""
    target = Path(path)
    target.write_text(svg_text, encoding="utf-8")
    return target
