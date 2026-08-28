from collections.abc import Iterator
from pathlib import Path

import pymupdf

from src.pdf_workbench.basic_ops import (
    find_contiguous_page_ranges,
    validate_pdf,
)
from src.pdf_workbench.page_ranges import parse_page_range


def parse_split_ranges(
    page_ranges: str,
    page_count: int,
) -> list[list[int]]:
    range_parts = [part.strip() for part in page_ranges.split(",")]
    if not page_ranges.strip() or any(not part for part in range_parts):
        raise ValueError("Enter ranges such as 1-5, 6-10, 11-end.")
    return [
        parse_page_range(range_part, page_count)
        for range_part in range_parts
    ]


def group_pages_by_count(
    page_count: int,
    pages_per_file: int,
) -> list[list[int]]:
    if pages_per_file < 1:
        raise ValueError("Pages per file must be at least 1.")
    return [
        list(range(first_page, min(first_page + pages_per_file, page_count)))
        for first_page in range(0, page_count, pages_per_file)
    ]


def create_single_page_groups(page_numbers: list[int]) -> list[list[int]]:
    if not page_numbers:
        raise ValueError("Select at least one page before splitting.")
    return [[page_number] for page_number in page_numbers]


def iter_split_pdf_parts(
    pdf_path: Path,
    page_groups: list[list[int]],
) -> Iterator[bytes]:
    if not page_groups:
        raise ValueError("Create at least one split part.")

    with pymupdf.open(pdf_path) as source_document:
        validate_page_groups(page_groups, source_document.page_count)
        for page_numbers in page_groups:
            output_document = pymupdf.open()
            try:
                for first_page, last_page in find_contiguous_page_ranges(
                    page_numbers
                ):
                    output_document.insert_pdf(
                        source_document,
                        from_page=first_page,
                        to_page=last_page,
                    )
                output_document.set_metadata(source_document.metadata)
                output_bytes = output_document.tobytes()
            finally:
                output_document.close()

            validate_pdf(output_bytes)
            yield output_bytes


def validate_page_groups(
    page_groups: list[list[int]],
    page_count: int,
) -> None:
    for page_numbers in page_groups:
        if not page_numbers:
            raise ValueError("A split part cannot be empty.")
        for page_number in page_numbers:
            if page_number < 0 or page_number >= page_count:
                raise ValueError(
                    f"Page {page_number + 1} is outside this "
                    f"{page_count}-page PDF."
                )
