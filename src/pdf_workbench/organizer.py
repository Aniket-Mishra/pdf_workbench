import pymupdf

from src.pdf_workbench.basic_ops import validate_pdf
from src.pdf_workbench.page_grid import GridPage
from src.pdf_workbench.page_images import (
    THUMBNAIL_WIDTH,
    RenderedPage,
    render_pages,
)
from src.pdf_workbench.workspace import StoredPdf


def list_page_ids(documents: list[StoredPdf]) -> list[str]:
    """Every page across the open PDFs as "document_index:page_index"."""
    return [
        f"{document_index}:{page_index}"
        for document_index, document in enumerate(documents)
        for page_index in range(document.page_count)
    ]


def split_page_id(page_id: str) -> tuple[int, int]:
    document_index, page_index = page_id.split(":")
    return int(document_index), int(page_index)


def render_organizer_thumbnails(
    documents: list[StoredPdf],
    page_ids: set[str],
) -> dict[str, RenderedPage]:
    page_numbers_by_document: dict[int, list[int]] = {}
    for page_id in page_ids:
        document_index, page_index = split_page_id(page_id)
        page_numbers_by_document.setdefault(document_index, []).append(
            page_index
        )

    thumbnails_by_id: dict[str, RenderedPage] = {}
    for document_index, page_numbers in page_numbers_by_document.items():
        document = documents[document_index]
        for thumbnail in render_pages(
            document.content_hash,
            str(document.path),
            tuple(sorted(page_numbers)),
            THUMBNAIL_WIDTH,
        ):
            thumbnails_by_id[f"{document_index}:{thumbnail.page_index}"] = (
                thumbnail
            )
    return thumbnails_by_id


def merge_pages_in_order(
    documents: list[StoredPdf],
    pages: list[GridPage],
) -> bytes:
    if not pages:
        raise ValueError("Keep at least one page in the organizer.")

    output_document = pymupdf.open()
    opened_documents: dict[int, pymupdf.Document] = {}
    try:
        for page in pages:
            document_index, page_index = split_page_id(page.source_page_id)
            if document_index not in opened_documents:
                opened_documents[document_index] = pymupdf.open(
                    documents[document_index].path
                )
            output_document.insert_pdf(
                opened_documents[document_index],
                from_page=page_index,
                to_page=page_index,
            )
            output_page = output_document[-1]
            output_page.set_rotation(
                (output_page.rotation + page.rotation) % 360
            )
        output_bytes = output_document.tobytes()
    finally:
        output_document.close()
        for opened_document in opened_documents.values():
            opened_document.close()

    validate_pdf(output_bytes)
    return output_bytes
