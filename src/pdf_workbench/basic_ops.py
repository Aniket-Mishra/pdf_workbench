import io
from pathlib import Path

import pikepdf
import pymupdf as fitz  # PyMuPDF


def merge_selected(
    pdfs: list[tuple[str, Path]], selections: dict[str, list[int]]
) -> bytes:
    output_document = fitz.open()
    try:
        for document_id, pdf_path in pdfs:
            with fitz.open(pdf_path) as source_document:
                selected_pages = selections.get(document_id, [])
                if not selected_pages:
                    output_document.insert_pdf(source_document)
                    continue

                for first_page, last_page in find_contiguous_page_ranges(
                    selected_pages
                ):
                    output_document.insert_pdf(
                        source_document,
                        from_page=first_page,
                        to_page=last_page,
                    )

        output_bytes = output_document.tobytes()
    finally:
        output_document.close()

    validate_pdf(output_bytes)
    return output_bytes


def filter_selected_per_file(
    pdf_path: Path, selected_pages: list[int]
) -> bytes:
    with fitz.open(pdf_path) as source_document:
        output_document = fitz.open()
        try:
            if not selected_pages:
                output_document.insert_pdf(source_document)
            else:
                for first_page, last_page in find_contiguous_page_ranges(
                    selected_pages
                ):
                    output_document.insert_pdf(
                        source_document,
                        from_page=first_page,
                        to_page=last_page,
                    )
            output_bytes = output_document.tobytes()
        finally:
            output_document.close()

    validate_pdf(output_bytes)
    return output_bytes


def find_contiguous_page_ranges(
    page_numbers: list[int],
) -> list[tuple[int, int]]:
    if not page_numbers:
        return []

    page_ranges: list[tuple[int, int]] = []
    first_page = previous_page = page_numbers[0]

    for page_number in page_numbers[1:]:
        if page_number == previous_page + 1:
            previous_page = page_number
            continue

        page_ranges.append((first_page, previous_page))
        first_page = previous_page = page_number

    page_ranges.append((first_page, previous_page))
    return page_ranges


def validate_pdf(pdf_bytes: bytes) -> None:
    with pikepdf.Pdf.open(io.BytesIO(pdf_bytes)) as document:
        syntax_warnings = document.check_pdf_syntax()

    if syntax_warnings:
        raise ValueError("Generated PDF failed structural validation.")
