from pathlib import Path

import streamlit as st

from src.pdf_workbench.page_filter_controls import filter_visible_pages
from src.pdf_workbench.page_grid import (
    GRID_LOAD_BATCH_SIZE,
    PageThumbnail,
    show_page_grid,
)
from src.pdf_workbench.page_images import THUMBNAIL_WIDTH, render_pages
from src.pdf_workbench.page_ranges import parse_page_range


def replace_selected_pages(
    document_id: str, selected_pages: list[int]
) -> None:
    grid_version_key = f"grid_version:{document_id}"
    st.session_state[f"selected_pages:{document_id}"] = selected_pages
    st.session_state[grid_version_key] = (
        st.session_state.get(grid_version_key, 0) + 1
    )
    st.rerun()


def show_page_controls(document_id: str, page_count: int) -> None:
    select_all_column, clear_column, _ = st.columns([1, 1, 4])
    if select_all_column.button(
        "Select all",
        key=f"select_all:{document_id}",
        width="stretch",
    ):
        replace_selected_pages(document_id, list(range(page_count)))
    if clear_column.button(
        "Clear",
        key=f"clear_all:{document_id}",
        width="stretch",
    ):
        replace_selected_pages(document_id, [])

    with st.form(f"page_range_form:{document_id}", border=False):
        range_column, apply_column = st.columns([5, 1])
        page_range = range_column.text_input(
            "Page range",
            placeholder="Page range, e.g. 1-5, 8, 12-end",
            label_visibility="collapsed",
        )
        apply_page_range = apply_column.form_submit_button(
            "Apply range",
            width="stretch",
        )

    if apply_page_range:
        try:
            selected_pages = parse_page_range(page_range, page_count)
        except ValueError as error:
            st.error(str(error))
        else:
            replace_selected_pages(document_id, selected_pages)


def show_filter_selection_controls(
    document_id: str,
    page_count: int,
    selected_pages: set[int],
    visible_page_numbers: tuple[int, ...],
) -> None:
    select_column, exclude_column, _ = st.columns([1, 1, 4])
    if select_column.button(
        "Select shown",
        key=f"select_shown:{document_id}",
        width="stretch",
    ):
        replace_selected_pages(document_id, list(visible_page_numbers))
    if exclude_column.button(
        "Exclude shown",
        key=f"exclude_shown:{document_id}",
        width="stretch",
    ):
        starting_pages = selected_pages or set(range(page_count))
        remaining_pages = starting_pages - set(visible_page_numbers)
        replace_selected_pages(document_id, sorted(remaining_pages))


def get_loaded_page_count(
    document_id: str,
    visible_page_numbers: tuple[int, ...],
) -> int:
    manifest_key = f"visible_pages:{document_id}"
    loaded_key = f"loaded_pages:{document_id}"
    if (
        st.session_state.get(manifest_key) != visible_page_numbers
        or loaded_key not in st.session_state
    ):
        st.session_state[manifest_key] = visible_page_numbers
        st.session_state[loaded_key] = min(
            GRID_LOAD_BATCH_SIZE,
            len(visible_page_numbers),
        )
    return st.session_state[loaded_key]


def select_pdf_pages(
    pdf_path: Path,
    content_hash: str,
    document_id: str,
    page_count: int,
) -> list[int]:
    selection_key = f"selected_pages:{document_id}"
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
        show_filter_selection_controls(
            document_id,
            page_count,
            selected_pages,
            page_numbers,
        )

    loaded_page_count = get_loaded_page_count(document_id, page_numbers)
    loaded_page_numbers = page_numbers[:loaded_page_count]
    images_by_page = {
        page.page_index: page.image_url
        for page in render_pages(
            content_hash,
            str(pdf_path),
            loaded_page_numbers,
            THUMBNAIL_WIDTH,
        )
    }
    grid_state = show_page_grid(
        pages=[
            PageThumbnail(
                page_id=str(page_number),
                caption=f"Page {page_number + 1}",
                image_url=images_by_page.get(page_number),
            )
            for page_number in page_numbers
        ],
        selected_ids={str(page_number) for page_number in selected_pages},
        selectable=True,
        reorderable=False,
        visible_page_count=loaded_page_count,
        key=(
            f"page_grid:{document_id}:"
            f"{st.session_state.get(f'grid_version:{document_id}', 0)}"
        ),
    )

    hidden_selected_pages = selected_pages - set(page_numbers)
    selected_page_numbers = sorted(
        hidden_selected_pages
        | {int(page_id) for page_id in grid_state.selected_ids}
    )
    st.session_state[selection_key] = selected_page_numbers

    if grid_state.action == "load_more":
        st.session_state[f"loaded_pages:{document_id}"] = min(
            loaded_page_count + GRID_LOAD_BATCH_SIZE,
            len(page_numbers),
        )
        st.rerun()

    return selected_page_numbers
