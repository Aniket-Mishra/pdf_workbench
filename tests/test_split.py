from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
import pytest

from src.pdf_workbench.split import (
    create_single_page_groups,
    group_pages_by_count,
    iter_split_pdf_parts,
    parse_split_ranges,
)
from src.pdf_workbench.split_controls import build_split_download
from src.pdf_workbench.workspace import StoredPdf


def create_pdf_file(
    pdf_path: Path,
    page_count: int,
    title: str = "",
) -> None:
    document = pymupdf.open()
    try:
        document.set_metadata({"title": title})
        for page_number in range(page_count):
            page = document.new_page()
            page.insert_text((72, 72), f"Page {page_number + 1}")
        document.save(pdf_path)
    finally:
        document.close()


def read_page_texts(pdf_bytes: bytes) -> list[str]:
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        return [page.get_text().strip() for page in document]


def test_parse_split_ranges_keeps_each_range_separate() -> None:
    assert parse_split_ranges("1-2, 3, 4-end", page_count=5) == [
        [0, 1],
        [2],
        [3, 4],
    ]


def test_group_pages_by_count_keeps_short_last_group() -> None:
    assert group_pages_by_count(page_count=7, pages_per_file=3) == [
        [0, 1, 2],
        [3, 4, 5],
        [6],
    ]


def test_single_page_groups_require_a_selection() -> None:
    with pytest.raises(ValueError, match="Select at least one page"):
        create_single_page_groups([])


def test_split_pdf_creates_requested_parts() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=5)
        output_files = list(
            iter_split_pdf_parts(pdf_path, [[0, 1], [3, 4]])
        )

    assert [read_page_texts(output) for output in output_files] == [
        ["Page 1", "Page 2"],
        ["Page 4", "Page 5"],
    ]


def test_split_pdf_preserves_document_metadata() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=2, title="Example")
        output_bytes = next(iter_split_pdf_parts(pdf_path, [[0]]))

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        assert document.metadata["title"] == "Example"


def test_split_pdf_rejects_pages_outside_document() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=2)

        with pytest.raises(ValueError, match="outside this 2-page PDF"):
            list(iter_split_pdf_parts(pdf_path, [[2]]))


def test_selected_page_split_skips_documents_without_selections() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        directory = Path(temporary_directory_name)
        first_path = directory / "first.pdf"
        second_path = directory / "second.pdf"
        create_pdf_file(first_path, page_count=2)
        create_pdf_file(second_path, page_count=2)
        documents = [
            StoredPdf("first", "first", "first.pdf", first_path, 2),
            StoredPdf("second", "second", "second.pdf", second_path, 2),
        ]

        output_name, output_bytes, mime_type = build_split_download(
            documents,
            {"first": [1], "second": []},
            "Selected pages",
            split_ranges="",
            pages_per_file=10,
        )

    assert output_name == "1_first_part_001.pdf"
    assert mime_type == "application/pdf"
    assert read_page_texts(output_bytes) == ["Page 2"]
