"""Write the CanRisk payload to disk and optionally open canrisk.org."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Protocol

CANRISK_UPLOAD_URL = "https://canrisk.org"


class BrowserLauncher(Protocol):
    def open(self, url: str) -> None: ...


class WebBrowserLauncher:
    """Concrete :class:`BrowserLauncher` using the stdlib ``webbrowser`` module."""

    def open(self, url: str) -> None:
        webbrowser.open(url)


class OutputSink:
    def __init__(self, *, output_dir: Path, browser: BrowserLauncher) -> None:
        self._output_dir = output_dir
        self._browser = browser

    def save(self, *, pedigree_id: str, payload: str) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / filename_for(pedigree_id)
        path.write_text(payload, encoding="utf-8")
        return path.resolve()

    def open_upload_page(self) -> None:
        self._browser.open(CANRISK_UPLOAD_URL)


def filename_for(pedigree_id: str) -> str:
    return f"evagene-canrisk-{pedigree_id[:8]}.txt"
