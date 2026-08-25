from pathlib import Path

import streamlit as st

from src.pdf_workbench.page_grid import PageThumbnail, show_page_grid
from src.pdf_workbench.page_ranges import parse_page_range
from src.pdf_workbench.thumbnails import render_page_thumbnails


def replace_selected_pages(
    document_id: str,
    selected_pages: list[int],
) -> None:
    selection_key = f"selected_pages:{document_id}"
    grid_version_key = f"grid_version:{document_id}"
    st.session_state[selection_key] = selected_pages
    st.session_state[grid_version_key] = (
        st.session_state.get(grid_version_key, 0) + 1
    )
    st.rerun()


def show_page_controls(
    document_id: str,
    page_count: int,
) -> None:
    select_all, clear_all, _ = st.columns([1, 1, 4])

    with select_all:
        if st.button("Select all", key=f"select_all:{document_id}"):
            replace_selected_pages(document_id, list(range(page_count)))

    with clear_all:
        if st.button("Clear", key=f"clear_all:{document_id}"):
            replace_selected_pages(document_id, [])

    with st.form(f"page_range_form:{document_id}", border=False):
        page_range = st.text_input(
            "Page range",
            placeholder="1-5, 8, 12-end",
        )
        apply_page_range = st.form_submit_button("Apply range")

    if apply_page_range:
        try:
            selected_pages = parse_page_range(page_range, page_count)
        except ValueError as error:
            st.error(str(error))
        else:
            replace_selected_pages(document_id, selected_pages)


def select_pdf_pages(
    pdf_path: Path,
    content_hash: str,
    document_id: str,
    page_count: int,
) -> list[int]:
    selection_key = f"selected_pages:{document_id}"
    grid_version_key = f"grid_version:{document_id}"

    selected_pages = set(st.session_state.get(selection_key, []))
    page_numbers = tuple(range(page_count))

    show_page_controls(document_id, page_count)

    thumbnails = render_page_thumbnails(
        content_hash,
        str(pdf_path),
        page_numbers,
    )
    pages = [
        PageThumbnail(
            page_id=str(page_number),
            image_bytes=thumbnail.image_bytes,
            image_mime_type=thumbnail.mime_type,
            caption=f"Page {page_number + 1}",
        )
        for page_number, thumbnail in zip(page_numbers, thumbnails)
    ]
    grid_state = show_page_grid(
        pages=pages,
        selected_ids={str(page_number) for page_number in selected_pages},
        selectable=True,
        reorderable=False,
        key=f"page_grid:{document_id}:"
        f"{st.session_state.get(grid_version_key, 0)}",
    )

    selected_page_numbers = sorted(
        int(page_id) for page_id in grid_state.selected_ids
    )
    st.session_state[selection_key] = selected_page_numbers
    return selected_page_numbers
