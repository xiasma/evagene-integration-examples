"""Pure transform from (embed URL, label, key) to an HTML snippet."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

_IFRAME_HEIGHT_PX = 640


@dataclass(frozen=True)
class SnippetRequest:
    embed_url: str
    label: str
    minted_at: str
    plaintext_key: str
    revoke_url: str


def build_snippet(request: SnippetRequest) -> str:
    src = escape(request.embed_url, quote=True)
    title = escape(request.label, quote=True)
    minted_at = escape(request.minted_at, quote=False)
    return (
        f"<!-- Evagene embeddable pedigree \u2014 read-only key minted {minted_at} -->\n"
        f'<iframe src="{src}" title="{title}" '
        f'width="100%" height="{_IFRAME_HEIGHT_PX}" frameborder="0"></iframe>\n'
        "\n"
        f"Minted API key: {request.plaintext_key}   "
        f"(stored only here \u2014 revoke at {request.revoke_url})\n"
    )
