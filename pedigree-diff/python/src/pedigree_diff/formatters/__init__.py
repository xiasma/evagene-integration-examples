"""Output formatters: one module per target format.

Every formatter implements :class:`Formatter` — a single
``render(diff, snapshot, options, sink) -> None`` method — so the
composition root can swap them behind one dispatch table.
"""

from .base import FormatOptions, Formatter
from .json_formatter import JsonFormatter
from .markdown_formatter import MarkdownFormatter
from .text_formatter import TextFormatter

__all__ = [
    "FormatOptions",
    "Formatter",
    "JsonFormatter",
    "MarkdownFormatter",
    "TextFormatter",
]
