from pathlib import Path

from canrisk_bridge.canrisk_client import CANRISK_HEADER
from canrisk_bridge.output_sink import OutputSink, filename_for

_PEDIGREE_ID = "a1cfe665-2e95-4386-9eb8-53d46095478a"


class _SpyBrowser:
    def __init__(self) -> None:
        self.opened: list[str] = []

    def open(self, url: str) -> None:
        self.opened.append(url)


def test_filename_uses_first_eight_chars_of_uuid() -> None:
    assert filename_for(_PEDIGREE_ID) == "evagene-canrisk-a1cfe665.txt"


def test_save_writes_payload_to_named_file_in_output_dir(tmp_path: Path) -> None:
    sink = OutputSink(output_dir=tmp_path, browser=_SpyBrowser())
    payload = f"{CANRISK_HEADER}\nFamID\tName\n"

    saved = sink.save(pedigree_id=_PEDIGREE_ID, payload=payload)

    assert saved == (tmp_path / "evagene-canrisk-a1cfe665.txt").resolve()
    assert saved.read_text(encoding="utf-8") == payload


def test_save_creates_missing_output_dir(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "dir"
    sink = OutputSink(output_dir=nested, browser=_SpyBrowser())

    sink.save(pedigree_id=_PEDIGREE_ID, payload=f"{CANRISK_HEADER}\n")

    assert nested.is_dir()


def test_open_upload_page_delegates_to_browser(tmp_path: Path) -> None:
    browser = _SpyBrowser()
    sink = OutputSink(output_dir=tmp_path, browser=browser)

    sink.open_upload_page()

    assert browser.opened == ["https://canrisk.org"]
