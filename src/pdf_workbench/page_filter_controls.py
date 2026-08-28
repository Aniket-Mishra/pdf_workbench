from pathlib import Path

import streamlit as st

from src.pdf_workbench.page_filters import (
    PageFacts,
    PageFilter,
    filter_page_numbers,
    load_page_facts,
)


def format_page_size(page_size: tuple[int, int]) -> str:
    width, height = page_size
    return f"{width} x {height} pt"


def show_filter_fields(
    document_id: str,
    page_facts: list[PageFacts],
) -> PageFilter:
    text_query = st.text_input(
        "Search page text",
        key=f"filter_text:{document_id}",
        placeholder="invoice, appendix, error code...",
    )
    use_regular_expression = st.checkbox(
        "Use regular expression",
        key=f"filter_regex:{document_id}",
        disabled=not text_query,
    )

    page_type_column, orientation_column, size_column = st.columns(3)
    with page_type_column:
        page_types = st.multiselect(
            "Page type",
            sorted({page.page_type for page in page_facts}),
            key=f"filter_types:{document_id}",
            placeholder="All types",
        )
    with orientation_column:
        orientations = st.multiselect(
            "Orientation",
            sorted({page.orientation for page in page_facts}),
            key=f"filter_orientations:{document_id}",
            placeholder="All orientations",
        )
    with size_column:
        page_sizes = st.multiselect(
            "Page size",
            sorted({page.size for page in page_facts}),
            format_func=format_page_size,
            key=f"filter_sizes:{document_id}",
            placeholder="All sizes",
        )

    return PageFilter(
        text_query=text_query,
        use_regular_expression=use_regular_expression,
        page_types=tuple(page_types),
        orientations=tuple(orientations),
        page_sizes=tuple(page_sizes),
    )


def filter_visible_pages(
    pdf_path: Path,
    content_hash: str,
    document_id: str,
    page_count: int,
) -> tuple[int, ...]:
    filters_enabled = st.toggle(
        "Search and filter pages",
        key=f"filter_enabled:{document_id}",
    )
    if not filters_enabled:
        return tuple(range(page_count))

    with st.spinner("Reading page text..."):
        page_facts = load_page_facts(content_hash, str(pdf_path))
    page_filter = show_filter_fields(document_id, page_facts)
    try:
        visible_page_numbers = tuple(
            filter_page_numbers(page_facts, page_filter)
        )
    except ValueError as error:
        st.error(str(error))
        return ()

    st.caption(f"{len(visible_page_numbers)} of {page_count} pages shown")
    return visible_page_numbers
