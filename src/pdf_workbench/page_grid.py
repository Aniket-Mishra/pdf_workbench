from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path

import streamlit.components.v1 as components


@dataclass(frozen=True)
class PageThumbnail:
    page_id: str
    image_bytes: bytes
    caption: str
    image_mime_type: str = "image/png"
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
    action_id: str | None


frontend_directory = Path(__file__).parent / "page_grid_frontend"
page_grid_component = components.declare_component(
    "page_grid",
    path=frontend_directory,
)


def show_page_grid(
    pages: list[PageThumbnail],
    selected_ids: set[str],
    selectable: bool,
    reorderable: bool,
    key: str,
    ordered_pages: list[GridPage] | None = None,
    reset_order_ids: list[str] | None = None,
) -> PageGridState:
    source_page_ids = {page.page_id for page in pages}
    default_ordered_pages = ordered_pages or [
        GridPage(page_id=page.page_id, source_page_id=page.page_id)
        for page in pages
    ]
    reset_page_ids = reset_order_ids or [
        page.page_id for page in default_ordered_pages
    ]
    if (
        len(reset_page_ids) != len(set(reset_page_ids))
        or any(page_id not in source_page_ids for page_id in reset_page_ids)
    ):
        reset_page_ids = [page.page_id for page in pages]

    default_value = {
        "ordered_pages": [
            {
                "id": page.page_id,
                "source_id": page.source_page_id,
                "rotation": page.rotation,
            }
            for page in default_ordered_pages
        ],
        "selected_ids": [
            page.page_id
            for page in default_ordered_pages
            if page.page_id in selected_ids
        ],
        "action": None,
        "action_id": None,
    }
    component_value = page_grid_component(
        pages=[
            {
                "id": page.page_id,
                "image": (
                    f"data:{page.image_mime_type};base64,"
                    + b64encode(page.image_bytes).decode("ascii")
                ),
                "caption": page.caption,
                "document_number": page.document_number,
                "document_name": page.document_name,
            }
            for page in pages
        ],
        ordered_pages=default_value["ordered_pages"],
        reset_order_ids=reset_page_ids,
        selected_ids=default_value["selected_ids"],
        selectable=selectable,
        reorderable=reorderable,
        default=default_value,
        key=key,
    )

    if not isinstance(component_value, dict):
        component_value = default_value

    parsed_ordered_pages = parse_ordered_pages(
        component_value.get("ordered_pages"),
        source_page_ids,
    )
    if not parsed_ordered_pages:
        parsed_ordered_pages = tuple(default_ordered_pages)
    if not reorderable and parsed_ordered_pages != tuple(
        default_ordered_pages
    ):
        parsed_ordered_pages = tuple(default_ordered_pages)

    active_page_ids = {page.page_id for page in parsed_ordered_pages}
    selected_id_values = component_value.get("selected_ids", [])
    if not isinstance(selected_id_values, list):
        selected_id_values = []
    selected_page_ids = tuple(
        page_id
        for page_id in selected_id_values
        if page_id in active_page_ids
    )

    action = component_value.get("action")
    if action != "build":
        action = None
    action_id = component_value.get("action_id")
    if not isinstance(action_id, str):
        action_id = None

    return PageGridState(
        ordered_pages=parsed_ordered_pages,
        selected_ids=selected_page_ids,
        action=action,
        action_id=action_id,
    )


def parse_ordered_pages(
    ordered_page_values: object,
    source_page_ids: set[str],
) -> tuple[GridPage, ...]:
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
        ordered_pages.append(
            GridPage(
                page_id=page_id,
                source_page_id=source_page_id,
                rotation=rotation,
            )
        )

    return tuple(ordered_pages)
