from dataclasses import dataclass
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# Thumbnails loaded per scroll step in both the selector and the organizer.
GRID_LOAD_BATCH_SIZE = 36


@dataclass(frozen=True)
class PageThumbnail:
    page_id: str
    caption: str
    image_url: str | None = None
    document_number: int | None = None
    document_name: str | None = None


@dataclass(frozen=True)
class GridPage:
    page_id: str
    source_page_id: str
    rotation: int = 0


@dataclass(frozen=True)
class PageGridState:
    ordered_pages: tuple[GridPage, ...]
    selected_ids: tuple[str, ...]
    action: str | None


page_grid_component = components.declare_component(
    "page_grid",
    path=Path(__file__).parent / "page_grid_frontend",
)


def show_page_grid(
    pages: list[PageThumbnail],
    selected_ids: set[str],
    selectable: bool,
    reorderable: bool,
    key: str,
    ordered_pages: list[GridPage] | None = None,
    visible_page_count: int | None = None,
) -> PageGridState:
    source_page_ids = {page.page_id for page in pages}
    if ordered_pages is None:
        ordered_pages = [
            GridPage(page.page_id, page.page_id) for page in pages
        ]
    if visible_page_count is None:
        visible_page_count = len(ordered_pages)

    default_value = {
        "ordered_pages": [
            {
                "id": page.page_id,
                "source_id": page.source_page_id,
                "rotation": page.rotation,
            }
            for page in ordered_pages
        ],
        "selected_ids": [
            page.page_id
            for page in ordered_pages
            if page.page_id in selected_ids
        ],
        "action": None,
        "action_id": None,
    }
    component_value = page_grid_component(
        pages=[
            {
                "id": page.page_id,
                "image": page.image_url,
                "caption": page.caption,
                "document_number": page.document_number,
                "document_name": page.document_name,
            }
            for page in pages
        ],
        ordered_pages=default_value["ordered_pages"],
        reset_order_ids=[page.page_id for page in pages],
        selected_ids=default_value["selected_ids"],
        selectable=selectable,
        reorderable=reorderable,
        visible_page_count=max(0, min(visible_page_count, len(ordered_pages))),
        default=default_value,
        key=key,
    )
    if not isinstance(component_value, dict):
        component_value = default_value

    parsed_pages = parse_ordered_pages(
        component_value.get("ordered_pages"),
        source_page_ids,
    )
    if not parsed_pages or not reorderable:
        parsed_pages = tuple(ordered_pages)

    active_page_ids = {page.page_id for page in parsed_pages}
    selected_values = component_value.get("selected_ids")
    if not isinstance(selected_values, list):
        selected_values = []

    # Streamlit re-sends the last value on every rerun; act on an id once.
    action = component_value.get("action")
    action_id = component_value.get("action_id")
    claimed_key = f"claimed_action:{key}"
    if (
        action not in {"build", "load_more"}
        or not isinstance(action_id, str)
        or st.session_state.get(claimed_key) == action_id
    ):
        action = None
    else:
        st.session_state[claimed_key] = action_id

    return PageGridState(
        ordered_pages=parsed_pages,
        selected_ids=tuple(
            page_id
            for page_id in selected_values
            if page_id in active_page_ids
        ),
        action=action,
    )


def parse_ordered_pages(
    ordered_page_values: object,
    source_page_ids: set[str],
) -> tuple[GridPage, ...]:
    """Validate the order sent back by the browser; reject anything odd."""
    if not isinstance(ordered_page_values, list):
        return ()

    ordered_pages: list[GridPage] = []
    used_page_ids: set[str] = set()
    for page_value in ordered_page_values:
        if not isinstance(page_value, dict):
            return ()

        page_id = page_value.get("id")
        source_page_id = page_value.get("source_id")
        rotation = page_value.get("rotation")
        if (
            not isinstance(page_id, str)
            or not page_id
            or page_id in used_page_ids
            or not isinstance(source_page_id, str)
            or source_page_id not in source_page_ids
            or not isinstance(rotation, int)
            or isinstance(rotation, bool)
            or rotation not in {0, 90, 180, 270}
        ):
            return ()

        used_page_ids.add(page_id)
        ordered_pages.append(GridPage(page_id, source_page_id, rotation))

    return tuple(ordered_pages)
