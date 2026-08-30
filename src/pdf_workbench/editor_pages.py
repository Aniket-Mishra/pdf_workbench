from dataclasses import dataclass

import pymupdf
import streamlit as st


EDITOR_PAGE_BATCH_SIZE = 8
EDITOR_PAGE_CACHE_ENTRIES = 12
EDITOR_PAGE_WIDTH = 1080
JPEG_QUALITY = 78


@dataclass(frozen=True)
class RenderedEditorPage:
    page_index: int
    image_bytes: bytes
    mime_type: str
    width_points: float
    height_points: float


@st.cache_data(show_spinner=False, max_entries=EDITOR_PAGE_CACHE_ENTRIES)
def render_editor_page_batch(
    content_hash: str,
    _pdf_path: str,
    page_numbers: tuple[int, ...],
) -> list[RenderedEditorPage]:
    rendered_pages: list[RenderedEditorPage] = []

    with pymupdf.open(_pdf_path) as document:
        for page_number in page_numbers:
            page = document[page_number]
            scale = EDITOR_PAGE_WIDTH / page.rect.width
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale),
                colorspace=pymupdf.csRGB,
                alpha=False,
            )
            if page.get_images():
                image_bytes = pixmap.tobytes(
                    "jpg",
                    jpg_quality=JPEG_QUALITY,
                )
                mime_type = "image/jpeg"
            else:
                image_bytes = pixmap.tobytes("png")
                mime_type = "image/png"

            rendered_pages.append(
                RenderedEditorPage(
                    page_index=page_number,
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    width_points=page.rect.width,
                    height_points=page.rect.height,
                )
            )

    return rendered_pages


def render_editor_pages(
    content_hash: str,
    pdf_path: str,
    loaded_page_count: int,
) -> list[RenderedEditorPage]:
    rendered_pages: list[RenderedEditorPage] = []
    for batch_start in range(0, loaded_page_count, EDITOR_PAGE_BATCH_SIZE):
        page_numbers = tuple(
            range(
                batch_start,
                min(batch_start + EDITOR_PAGE_BATCH_SIZE, loaded_page_count),
            )
        )
        rendered_pages.extend(
            render_editor_page_batch(content_hash, pdf_path, page_numbers)
        )
    return rendered_pages


def clear_editor_page_cache() -> None:
    render_editor_page_batch.clear()
