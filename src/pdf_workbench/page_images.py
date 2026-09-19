from base64 import b64encode
from dataclasses import dataclass

import pymupdf
import streamlit as st


RENDER_BATCH_SIZE = 12
RENDER_CACHE_ENTRIES = 48
THUMBNAIL_WIDTH = 200
EDITOR_PAGE_WIDTH = 1080
JPEG_QUALITY = 75


@dataclass(frozen=True)
class RenderedPage:
    page_index: int
    image_url: str
    width_points: float
    height_points: float


@st.cache_data(show_spinner=False, max_entries=RENDER_CACHE_ENTRIES)
def render_page_batch(
    content_hash: str,
    _pdf_path: str,
    page_numbers: tuple[int, ...],
    image_width: int,
) -> list[RenderedPage]:
    rendered_pages: list[RenderedPage] = []
    with pymupdf.open(_pdf_path) as document:
        for page_number in page_numbers:
            page = document[page_number]
            scale = image_width / page.rect.width
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale),
                colorspace=pymupdf.csRGB,
                alpha=False,
            )
            # JPEG for photo-like pages, PNG keeps text crisp and small.
            if page.get_images():
                image_bytes = pixmap.tobytes("jpg", jpg_quality=JPEG_QUALITY)
                mime_type = "image/jpeg"
            else:
                image_bytes = pixmap.tobytes("png")
                mime_type = "image/png"
            rendered_pages.append(
                RenderedPage(
                    page_index=page_number,
                    image_url=(
                        f"data:{mime_type};base64,"
                        + b64encode(image_bytes).decode("ascii")
                    ),
                    width_points=page.rect.width,
                    height_points=page.rect.height,
                )
            )
    return rendered_pages


def render_pages(
    content_hash: str,
    pdf_path: str,
    page_numbers: tuple[int, ...],
    image_width: int,
) -> list[RenderedPage]:
    rendered_pages: list[RenderedPage] = []
    for batch_start in range(0, len(page_numbers), RENDER_BATCH_SIZE):
        page_batch = page_numbers[
            batch_start : batch_start + RENDER_BATCH_SIZE
        ]
        rendered_pages.extend(
            render_page_batch(content_hash, pdf_path, page_batch, image_width)
        )
    return rendered_pages


def clear_page_image_cache() -> None:
    render_page_batch.clear()
