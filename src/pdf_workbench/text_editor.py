from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from src.pdf_workbench.basic_ops import validate_pdf
from src.pdf_workbench.marks import Mark, apply_marks


MINIMUM_FONT_SIZE = 8
MAXIMUM_FONT_SIZE = 72


@dataclass(frozen=True)
class TextEdit:
    page_index: int
    text: str
    font_size: int
    horizontal_position: float
    vertical_position: float


def create_edited_pdf(
    pdf_path: Path,
    text_edits: list[TextEdit],
    marks: Sequence[Mark] = (),
) -> bytes:
    if not text_edits and not marks:
        raise ValueError("Add text or a drawing before creating the PDF.")

    with pymupdf.open(pdf_path) as document:
        clear_rotated_pages(
            document,
            {text_edit.page_index for text_edit in text_edits}
            | {mark.page_index for mark in marks},
        )
        apply_text_edits(document, text_edits)
        apply_marks(document, marks)
        output_bytes = document.tobytes()

    validate_pdf(output_bytes)
    return output_bytes


def clear_rotated_pages(
    document: pymupdf.Document,
    page_indexes: set[int],
) -> None:
    for page_index in page_indexes:
        if (
            isinstance(page_index, bool)
            or not isinstance(page_index, int)
            or not 0 <= page_index < document.page_count
        ):
            continue
        page = document[page_index]
        if page.rotation:
            page.remove_rotation()


def apply_text_edits(
    document: pymupdf.Document,
    text_edits: list[TextEdit],
) -> None:
    for text_edit in text_edits:
        validate_page_index(document, text_edit.page_index)
        insert_text_edit(document[text_edit.page_index], text_edit)


def insert_text_edit(page: pymupdf.Page, text_edit: TextEdit) -> None:
    text = text_edit.text.strip()
    if not text:
        raise ValueError("Text cannot be empty.")
    validate_text_characters(text)
    if not MINIMUM_FONT_SIZE <= text_edit.font_size <= MAXIMUM_FONT_SIZE:
        raise ValueError(
            f"Text size must be {MINIMUM_FONT_SIZE} to {MAXIMUM_FONT_SIZE}."
        )
    if not 0 <= text_edit.horizontal_position <= 1:
        raise ValueError("Horizontal position must be between 0 and 1.")
    if not 0 <= text_edit.vertical_position <= 1:
        raise ValueError("Vertical position must be between 0 and 1.")

    text_width = pymupdf.get_text_length(
        text,
        fontname="helv",
        fontsize=text_edit.font_size,
    )
    if text_width > page.rect.width:
        raise ValueError("Text is too wide. Reduce its size or shorten it.")
    if text_edit.font_size > page.rect.height:
        raise ValueError("Text is too tall. Reduce its size.")

    requested_x_position = page.rect.width * text_edit.horizontal_position
    x_position = min(
        requested_x_position,
        page.rect.width - text_width,
    )
    y_position = (
        page.rect.height * text_edit.vertical_position
        + text_edit.font_size
    )
    if y_position > page.rect.height:
        raise ValueError("Text is too low. Move it higher on the page.")

    page.insert_text(
        (x_position, y_position),
        text,
        fontname="helv",
        fontsize=text_edit.font_size,
        color=(0, 0, 0),
        overlay=True,
    )


def validate_text_characters(text: str) -> None:
    font = pymupdf.Font(fontname="helv")
    unsupported_character = next(
        (
            character
            for character in text
            if not character.isspace()
            and not font.has_glyph(ord(character))
        ),
        None,
    )
    if unsupported_character:
        raise ValueError(
            f'The current font cannot display "{unsupported_character}".'
        )


def validate_page_index(
    document: pymupdf.Document,
    page_index: int,
) -> None:
    if not 0 <= page_index < document.page_count:
        raise ValueError(f"Page {page_index + 1} does not exist.")
