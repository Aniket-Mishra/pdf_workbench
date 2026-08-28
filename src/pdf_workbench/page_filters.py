import re
from dataclasses import dataclass

import pymupdf
import streamlit as st


PAGE_FACT_CACHE_ENTRIES = 8


@dataclass(frozen=True)
class PageFacts:
    page_number: int
    text: str
    width_points: int
    height_points: int
    orientation: str
    page_type: str

    @property
    def size(self) -> tuple[int, int]:
        return self.width_points, self.height_points


@dataclass(frozen=True)
class PageFilter:
    text_query: str = ""
    use_regular_expression: bool = False
    page_types: tuple[str, ...] = ()
    orientations: tuple[str, ...] = ()
    page_sizes: tuple[tuple[int, int], ...] = ()


def classify_page(page: pymupdf.Page, text: str) -> str:
    if text:
        return "Text"
    if page.get_images(full=True):
        return "Scanned"
    if page.get_drawings():
        return "Graphics"
    return "Blank"


def identify_orientation(width: float, height: float) -> str:
    if abs(width - height) < 1:
        return "Square"
    if width > height:
        return "Landscape"
    return "Portrait"


@st.cache_data(show_spinner=False, max_entries=PAGE_FACT_CACHE_ENTRIES)
def load_page_facts(
    content_hash: str,
    _pdf_path: str,
) -> list[PageFacts]:
    page_facts: list[PageFacts] = []
    with pymupdf.open(_pdf_path) as document:
        for page_number, page in enumerate(document):
            text = page.get_text().strip()
            width = page.rect.width
            height = page.rect.height
            page_facts.append(
                PageFacts(
                    page_number=page_number,
                    text=text,
                    width_points=round(width),
                    height_points=round(height),
                    orientation=identify_orientation(width, height),
                    page_type=classify_page(page, text),
                )
            )
    return page_facts


def filter_page_numbers(
    page_facts: list[PageFacts],
    page_filter: PageFilter,
) -> list[int]:
    text_pattern = compile_text_pattern(page_filter)
    return [
        page.page_number
        for page in page_facts
        if page_matches_filter(page, page_filter, text_pattern)
    ]


def compile_text_pattern(page_filter: PageFilter) -> re.Pattern[str] | None:
    if not page_filter.text_query or not page_filter.use_regular_expression:
        return None
    try:
        return re.compile(page_filter.text_query, re.IGNORECASE)
    except re.error as error:
        raise ValueError(f"Invalid regular expression: {error}.") from error


def page_matches_filter(
    page: PageFacts,
    page_filter: PageFilter,
    text_pattern: re.Pattern[str] | None,
) -> bool:
    if page_filter.page_types and page.page_type not in page_filter.page_types:
        return False
    if (
        page_filter.orientations
        and page.orientation not in page_filter.orientations
    ):
        return False
    if page_filter.page_sizes and page.size not in page_filter.page_sizes:
        return False
    if not page_filter.text_query:
        return True
    if text_pattern:
        return bool(text_pattern.search(page.text))
    return page_filter.text_query.casefold() in page.text.casefold()


def clear_page_facts_cache() -> None:
    load_page_facts.clear()
