from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
import pytest

from src.pdf_workbench.text_editor import (
    TextEdit,
    create_edited_pdf,
)


def create_pdf_file(pdf_path: Path, page_count: int = 2) -> None:
    document = pymupdf.open()
    try:
        document.set_metadata({"title": "Original"})
        for page_number in range(page_count):
            page = document.new_page()
            page.insert_text((72, 72), f"Page {page_number + 1}")
        document.save(pdf_path)
    finally:
        document.close()


def create_text_edit(page_index: int, text: str) -> TextEdit:
    return TextEdit(
        page_index=page_index,
        text=text,
        font_size=18,
        horizontal_position=0.25,
        vertical_position=0.5,
    )


def test_create_edited_pdf_adds_text_to_requested_pages() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path)

        output_bytes = create_edited_pdf(
            pdf_path,
            [
                create_text_edit(0, "First edit"),
                create_text_edit(1, "Second edit"),
            ],
        )

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        assert "First edit" in document[0].get_text()
        assert "Second edit" in document[1].get_text()
        assert document.metadata["title"] == "Original"


def test_create_edited_pdf_handles_rotated_pages() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "rotated.pdf"
        create_pdf_file(pdf_path, page_count=1)
        with pymupdf.open(pdf_path) as document:
            document[0].set_rotation(90)
            document.saveIncr()

        output_bytes = create_edited_pdf(
            pdf_path,
            [create_text_edit(0, "Rotated edit")],
        )

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        assert "Rotated edit" in document[0].get_text()
        assert document[0].rotation == 0


def test_create_edited_pdf_uses_requested_size_and_position() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=1)
        text_edit = TextEdit(
            page_index=0,
            text="Positioned text",
            font_size=30,
            horizontal_position=0.25,
            vertical_position=0.8,
        )

        output_bytes = create_edited_pdf(pdf_path, [text_edit])

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        page_rect = document[0].rect
        text_spans = [
            span
            for block in document[0].get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
            if span["text"] == "Positioned text"
        ]

    assert len(text_spans) == 1
    assert text_spans[0]["size"] == pytest.approx(30)
    assert text_spans[0]["origin"][0] == pytest.approx(
        page_rect.width * 0.25,
    )
    assert text_spans[0]["origin"][1] == pytest.approx(
        page_rect.height * 0.8 + 30,
    )


def test_create_edited_pdf_keeps_text_inside_right_edge() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=1)
        text_edit = TextEdit(
            page_index=0,
            text="Visible text",
            font_size=30,
            horizontal_position=0.98,
            vertical_position=0.5,
        )

        output_bytes = create_edited_pdf(pdf_path, [text_edit])

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        assert "Visible text" in document[0].get_text()


def test_create_edited_pdf_rejects_text_that_does_not_fit() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=1)

        with pytest.raises(ValueError, match="Text is too wide"):
            create_edited_pdf(
                pdf_path,
                [create_text_edit(0, "Text " * 100)],
            )


def test_create_edited_pdf_rejects_unsupported_characters() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=1)

        with pytest.raises(ValueError, match="cannot display"):
            create_edited_pdf(
                pdf_path,
                [create_text_edit(0, "Check ✓")],
            )


def test_create_edited_pdf_rejects_text_below_page() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=1)

        with pytest.raises(ValueError, match="too low"):
            create_edited_pdf(
                pdf_path,
                [
                    TextEdit(
                        page_index=0,
                        text="Too low",
                        font_size=18,
                        horizontal_position=0.5,
                        vertical_position=1,
                    )
                ],
            )
