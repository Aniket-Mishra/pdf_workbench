from dataclasses import dataclass

import pymupdf as fitz
import streamlit as st


THUMBNAIL_BATCH_SIZE = 36
THUMBNAIL_CACHE_ENTRIES = 24
THUMBNAIL_WIDTH = 200
JPEG_QUALITY = 72


@dataclass(frozen=True)
class RenderedThumbnail:
    image_bytes: bytes
    mime_type: str


def encode_thumbnail(
    pixmap: fitz.Pixmap,
    use_jpeg: bool,
) -> RenderedThumbnail:
    if use_jpeg:
        image_bytes = pixmap.tobytes("jpg", jpg_quality=JPEG_QUALITY)
        return RenderedThumbnail(image_bytes, "image/jpeg")
    return RenderedThumbnail(pixmap.tobytes("png"), "image/png")


@st.cache_data(show_spinner=False, max_entries=THUMBNAIL_CACHE_ENTRIES)
def render_thumbnail_batch(
    content_hash: str,
    _pdf_path: str,
    page_numbers: tuple[int, ...],
    thumbnail_width: int = THUMBNAIL_WIDTH,
) -> list[RenderedThumbnail]:
    thumbnails: list[RenderedThumbnail] = []

    with fitz.open(_pdf_path) as document:
        for page_number in page_numbers:
            page = document[page_number]
            scale = thumbnail_width / page.rect.width
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale),
                colorspace=fitz.csRGB,
                alpha=False,
            )
            thumbnails.append(
                encode_thumbnail(
                    pixmap,
                    use_jpeg=bool(page.get_images()),
                )
            )

    return thumbnails


def render_page_thumbnails(
    content_hash: str,
    pdf_path: str,
    page_numbers: tuple[int, ...],
    thumbnail_width: int = THUMBNAIL_WIDTH,
) -> list[RenderedThumbnail]:
    thumbnails: list[RenderedThumbnail] = []
    for batch_start in range(0, len(page_numbers), THUMBNAIL_BATCH_SIZE):
        page_batch = page_numbers[
            batch_start : batch_start + THUMBNAIL_BATCH_SIZE
        ]
        thumbnails.extend(
            render_thumbnail_batch(
                content_hash,
                pdf_path,
                page_batch,
                thumbnail_width,
            )
        )
    return thumbnails


def clear_thumbnail_cache() -> None:
    render_thumbnail_batch.clear()
