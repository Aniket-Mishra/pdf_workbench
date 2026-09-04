import io
from pathlib import Path

import pikepdf
import pymupdf


def merge_selected(
    pdf_documents: list[tuple[str, Path]],
    selections: dict[str, list[int]],
) -> bytes:
    if not pdf_documents:
        raise ValueError("Open at least one PDF before merging.")

    output_document = pymupdf.open()
    try:
        for document_id, pdf_path in pdf_documents:
            with pymupdf.open(pdf_path) as source_document:
                selected_pages = selections.get(document_id, [])
                insert_selected_pages(
                    output_document,
                    source_document,
                    selected_pages,
                )

        output_bytes = output_document.tobytes()
    finally:
        output_document.close()

    validate_pdf(output_bytes)
    return output_bytes


def export_selected_pages(
    pdf_path: Path, selected_pages: list[int]
) -> bytes:
    with pymupdf.open(pdf_path) as source_document:
        output_document = pymupdf.open()
        try:
            insert_selected_pages(
                output_document,
                source_document,
                selected_pages,
            )
            output_document.set_metadata(source_document.metadata)
            output_bytes = output_document.tobytes()
        finally:
            output_document.close()

    validate_pdf(output_bytes)
    return output_bytes


def insert_selected_pages(
    output_document: pymupdf.Document,
    source_document: pymupdf.Document,
    selected_pages: list[int],
) -> None:
    if not selected_pages:
        output_document.insert_pdf(source_document)
        return

    for first_page, last_page in find_contiguous_page_ranges(selected_pages):
        output_document.insert_pdf(
            source_document,
            from_page=first_page,
            to_page=last_page,
        )


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
    try:
        with pikepdf.Pdf.open(
            io.BytesIO(pdf_bytes),
            attempt_recovery=False,
        ) as document:
            page_count = len(document.pages)
    except pikepdf.PdfError as error:
        raise ValueError(
            "Generated PDF failed structural validation."
        ) from error

    if page_count == 0:
        raise ValueError("Generated PDF failed structural validation.")
