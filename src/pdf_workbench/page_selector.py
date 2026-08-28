from pathlib import Path

import streamlit as st

from src.pdf_workbench.page_filter_controls import filter_visible_pages
from src.pdf_workbench.page_grid import PageThumbnail, show_page_grid
from src.pdf_workbench.page_ranges import parse_page_range
from src.pdf_workbench.thumbnails import (
    THUMBNAIL_BATCH_SIZE,
    render_page_thumbnails,
)


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


def select_visible_pages(
    document_id: str,
    page_count: int,
    selected_pages: set[int],
    visible_page_numbers: tuple[int, ...],
) -> None:
    select_matches, exclude_matches, _ = st.columns([1, 1, 3])
    with select_matches:
        if st.button("Select shown", key=f"select_shown:{document_id}"):
            replace_selected_pages(document_id, list(visible_page_numbers))
    with exclude_matches:
        if st.button("Exclude shown", key=f"exclude_shown:{document_id}"):
            starting_pages = selected_pages or set(range(page_count))
            remaining_pages = starting_pages - set(visible_page_numbers)
            replace_selected_pages(document_id, sorted(remaining_pages))


def get_loaded_page_count(
    document_id: str,
    visible_page_numbers: tuple[int, ...],
) -> int:
    page_manifest_key = f"visible_pages:{document_id}"
    loaded_page_count_key = f"loaded_pages:{document_id}"
    if (
        st.session_state.get(page_manifest_key) != visible_page_numbers
        or loaded_page_count_key not in st.session_state
    ):
        st.session_state[page_manifest_key] = visible_page_numbers
        st.session_state[loaded_page_count_key] = min(
            THUMBNAIL_BATCH_SIZE,
            len(visible_page_numbers),
        )
    return st.session_state[loaded_page_count_key]


def select_pdf_pages(
    pdf_path: Path,
    content_hash: str,
    document_id: str,
    page_count: int,
) -> list[int]:
    selection_key = f"selected_pages:{document_id}"
    grid_version_key = f"grid_version:{document_id}"

    selected_pages = set(st.session_state.get(selection_key, []))

    show_page_controls(document_id, page_count)
    page_numbers = filter_visible_pages(
        pdf_path,
        content_hash,
        document_id,
        page_count,
    )
    if not page_numbers:
        st.info("No pages match these filters.")
        return sorted(selected_pages)

    if st.session_state.get(f"filter_enabled:{document_id}"):
        select_visible_pages(
            document_id,
            page_count,
            selected_pages,
            page_numbers,
        )

    loaded_page_count = get_loaded_page_count(document_id, page_numbers)
    loaded_page_numbers = page_numbers[:loaded_page_count]
    thumbnails = render_page_thumbnails(
        content_hash,
        str(pdf_path),
        loaded_page_numbers,
    )
    thumbnails_by_page = dict(zip(loaded_page_numbers, thumbnails))
    pages = [
        PageThumbnail(
            page_id=str(page_number),
            image_bytes=(
                thumbnails_by_page[page_number].image_bytes
                if page_number in thumbnails_by_page
                else None
            ),
            image_mime_type=(
                thumbnails_by_page[page_number].mime_type
                if page_number in thumbnails_by_page
                else "image/png"
            ),
            caption=f"Page {page_number + 1}",
        )
        for page_number in page_numbers
    ]
    grid_state = show_page_grid(
        pages=pages,
        selected_ids={str(page_number) for page_number in selected_pages},
        selectable=True,
        reorderable=False,
        visible_page_count=loaded_page_count,
        key=f"page_grid:{document_id}:"
        f"{st.session_state.get(grid_version_key, 0)}",
    )

    selected_visible_pages = {
        int(page_id) for page_id in grid_state.selected_ids
    }
    hidden_selected_pages = selected_pages - set(page_numbers)
    selected_page_numbers = sorted(
        hidden_selected_pages | selected_visible_pages
    )
    st.session_state[selection_key] = selected_page_numbers

    load_action_key = f"load_more_action:{document_id}"
    new_load_requested = (
        grid_state.action == "load_more"
        and grid_state.action_id is not None
        and grid_state.action_id != st.session_state.get(load_action_key)
    )
    if new_load_requested:
        st.session_state[load_action_key] = grid_state.action_id
        st.session_state[f"loaded_pages:{document_id}"] = min(
            loaded_page_count + THUMBNAIL_BATCH_SIZE,
            len(page_numbers),
        )
        st.rerun()

    return selected_page_numbers
