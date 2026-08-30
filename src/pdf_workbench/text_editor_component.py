from base64 import b64encode
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import streamlit.components.v1 as components

from src.pdf_workbench.editor_pages import RenderedEditorPage
from src.pdf_workbench.text_editor import (
    MAXIMUM_FONT_SIZE,
    MINIMUM_FONT_SIZE,
    TextEdit,
)


MAXIMUM_TEXT_LENGTH = 500


@dataclass(frozen=True)
class TextEditorState:
    text_edits: tuple[TextEdit, ...]
    action: str | None
    action_id: str | None


frontend_directory = Path(__file__).parent / "text_editor_frontend"
text_editor_component = components.declare_component(
    "text_editor_canvas",
    path=frontend_directory,
)


def serialize_text_edits(text_edits: list[TextEdit]) -> list[dict]:
    return [
        {
            "id": f"saved-text-{edit_number}",
            "page_index": text_edit.page_index,
            "text": text_edit.text,
            "font_size": text_edit.font_size,
            "horizontal_position": text_edit.horizontal_position,
            "vertical_position": text_edit.vertical_position,
        }
        for edit_number, text_edit in enumerate(text_edits)
    ]


def parse_text_edits(
    text_edit_values: object,
    page_count: int,
) -> tuple[TextEdit, ...] | None:
    if not isinstance(text_edit_values, list):
        return None

    text_edits: list[TextEdit] = []
    for text_edit_value in text_edit_values:
        text_edit = parse_text_edit(text_edit_value, page_count)
        if text_edit is None:
            return None
        text_edits.append(text_edit)
    return tuple(text_edits)


def parse_text_edit(
    text_edit_value: object,
    page_count: int,
) -> TextEdit | None:
    if not isinstance(text_edit_value, dict):
        return None

    page_index = text_edit_value.get("page_index")
    text = text_edit_value.get("text")
    font_size = text_edit_value.get("font_size")
    horizontal_position = text_edit_value.get("horizontal_position")
    vertical_position = text_edit_value.get("vertical_position")

    if (
        not isinstance(page_index, int)
        or isinstance(page_index, bool)
        or not 0 <= page_index < page_count
        or not isinstance(text, str)
        or not text.strip()
        or len(text) > MAXIMUM_TEXT_LENGTH
        or "\n" in text
        or "\r" in text
        or not isinstance(font_size, int)
        or isinstance(font_size, bool)
        or not MINIMUM_FONT_SIZE <= font_size <= MAXIMUM_FONT_SIZE
        or not is_valid_position(horizontal_position)
        or not is_valid_position(vertical_position)
    ):
        return None

    return TextEdit(
        page_index=page_index,
        text=text.strip(),
        font_size=font_size,
        horizontal_position=float(horizontal_position),
        vertical_position=float(vertical_position),
    )


def is_valid_position(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and 0 <= value <= 1
    )


def show_text_editor(
    document_id: str,
    pages: list[RenderedEditorPage],
    page_count: int,
    text_edits: list[TextEdit],
    download_ready: bool,
    key: str,
) -> TextEditorState:
    serialized_text_edits = serialize_text_edits(text_edits)
    default_value = {
        "text_edits": serialized_text_edits,
        "action": None,
        "action_id": None,
    }
    component_value = text_editor_component(
        document_id=document_id,
        pages=[
            {
                "page_index": page.page_index,
                "image": (
                    f"data:{page.mime_type};base64,"
                    + b64encode(page.image_bytes).decode("ascii")
                ),
                "width_points": page.width_points,
                "height_points": page.height_points,
            }
            for page in pages
        ],
        page_count=page_count,
        text_edits=serialized_text_edits,
        minimum_font_size=MINIMUM_FONT_SIZE,
        maximum_font_size=MAXIMUM_FONT_SIZE,
        maximum_text_length=MAXIMUM_TEXT_LENGTH,
        download_ready=download_ready,
        default=default_value,
        key=key,
    )
    if not isinstance(component_value, dict):
        component_value = default_value

    parsed_text_edits = parse_text_edits(
        component_value.get("text_edits"),
        page_count,
    )
    if parsed_text_edits is None:
        parsed_text_edits = tuple(text_edits)

    action = component_value.get("action")
    if action not in {"change", "load_more", "build"}:
        action = None
    action_id = component_value.get("action_id")
    if not isinstance(action_id, str):
        action_id = None

    return TextEditorState(
        text_edits=parsed_text_edits,
        action=action,
        action_id=action_id,
    )
