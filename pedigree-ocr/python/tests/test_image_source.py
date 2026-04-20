from pathlib import Path
from typing import cast

import pytest

from pedigree_ocr.image_source import (
    JPEG_MEDIA_TYPE,
    PNG_MEDIA_TYPE,
    ImageSourceError,
    PdfRenderer,
    load_image,
)

FIXTURE_PNG = Path(__file__).resolve().parents[2] / "fixtures" / "sample-pedigree-drawing.png"


class _FakePdfRenderer:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.last_path: Path | None = None

    def render_first_page_as_png(self, path: Path) -> bytes:
        self.last_path = path
        return self._payload


def test_png_is_returned_verbatim() -> None:
    image = load_image(FIXTURE_PNG)

    assert image.media_type == PNG_MEDIA_TYPE
    assert image.data == FIXTURE_PNG.read_bytes()


def test_jpeg_extension_maps_to_jpeg_media_type(tmp_path: Path) -> None:
    path = tmp_path / "drawing.jpg"
    path.write_bytes(b"fake jpeg bytes")

    image = load_image(path)

    assert image.media_type == JPEG_MEDIA_TYPE
    assert image.data == b"fake jpeg bytes"


def test_pdf_is_rendered_to_png_via_injected_renderer(tmp_path: Path) -> None:
    pdf_path = tmp_path / "drawing.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    renderer = _FakePdfRenderer(payload=b"rendered-png-bytes")

    image = load_image(pdf_path, pdf_renderer=cast("PdfRenderer", renderer))

    assert image.media_type == PNG_MEDIA_TYPE
    assert image.data == b"rendered-png-bytes"
    assert renderer.last_path == pdf_path


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    path = tmp_path / "drawing.bmp"
    path.write_bytes(b"bmp")

    with pytest.raises(ImageSourceError, match="Unsupported"):
        load_image(path)


def test_missing_file_raises_image_source_error(tmp_path: Path) -> None:
    with pytest.raises(ImageSourceError, match="Could not read"):
        load_image(tmp_path / "does-not-exist.png")
