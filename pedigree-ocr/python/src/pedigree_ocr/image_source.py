"""Load a pedigree image from disk as a bytes-plus-media-type pair.

``.png`` / ``.jpg`` / ``.jpeg`` are returned verbatim. ``.pdf`` is
rendered to a single PNG via ``pdf2image`` (which requires Poppler on
Windows -- see the demo README). One responsibility: turn a file path
into something the Anthropic image content block accepts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

PNG_MEDIA_TYPE = "image/png"
JPEG_MEDIA_TYPE = "image/jpeg"

_EXTENSION_MEDIA_TYPES: dict[str, str] = {
    ".png": PNG_MEDIA_TYPE,
    ".jpg": JPEG_MEDIA_TYPE,
    ".jpeg": JPEG_MEDIA_TYPE,
}
_PDF_EXTENSION = ".pdf"


class ImageSourceError(ValueError):
    """Raised when an image file cannot be read or is unsupported."""


@dataclass(frozen=True)
class LoadedImage:
    data: bytes
    media_type: str

    @property
    def size_kb(self) -> int:
        return max(1, len(self.data) // 1024)


class PdfRenderer(Protocol):
    """Narrow surface over ``pdf2image`` so tests can fake it."""

    def render_first_page_as_png(self, path: Path) -> bytes: ...


def load_image(path: Path, *, pdf_renderer: PdfRenderer | None = None) -> LoadedImage:
    extension = path.suffix.lower()
    if extension in _EXTENSION_MEDIA_TYPES:
        return LoadedImage(data=_read_bytes(path), media_type=_EXTENSION_MEDIA_TYPES[extension])
    if extension == _PDF_EXTENSION:
        renderer = pdf_renderer or _Pdf2ImageRenderer()
        return LoadedImage(data=renderer.render_first_page_as_png(path), media_type=PNG_MEDIA_TYPE)
    raise ImageSourceError(
        f"Unsupported image extension {extension!r}: expected .png, .jpg, .jpeg, or .pdf."
    )


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ImageSourceError(f"Could not read image {path}: {exc}") from exc


class _Pdf2ImageRenderer:
    """Concrete :class:`PdfRenderer` backed by ``pdf2image``."""

    def render_first_page_as_png(self, path: Path) -> bytes:
        from io import BytesIO

        from pdf2image import convert_from_path
        from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError

        try:
            pages = convert_from_path(str(path), first_page=1, last_page=1, fmt="png")
        except (PDFPageCountError, PDFSyntaxError, OSError) as exc:
            raise ImageSourceError(
                f"Could not render PDF {path}. Is Poppler installed? ({exc})"
            ) from exc
        if not pages:
            raise ImageSourceError(f"PDF {path} contained no pages.")
        buffer = BytesIO()
        pages[0].save(buffer, format="PNG")
        return buffer.getvalue()
