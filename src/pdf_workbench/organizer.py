from dataclasses import dataclass

import pymupdf

from src.pdf_workbench.basic_ops import validate_pdf
from src.pdf_workbench.thumbnails import (
    RenderedThumbnail,
    render_page_thumbnails,
)
from src.pdf_workbench.workspace import StoredPdf


@dataclass(frozen=True)
class PageReference:
    document_index: int
    page_index: int
    uid: str


@dataclass(frozen=True)
class PagePlacement:
    instance_id: str
    source_page_id: str
    rotation: int = 0


def build_page_references(documents: list[StoredPdf]) -> list[PageReference]:
    page_references: list[PageReference] = []
    for document_index, document in enumerate(documents):
        for page_index in range(document.page_count):
            page_references.append(
                PageReference(
                    document_index=document_index,
                    page_index=page_index,
                    uid=f"{document_index}:{page_index}",
                )
            )
    return page_references


def create_initial_page_placements(
    page_references: list[PageReference],
) -> list[PagePlacement]:
    return [
        PagePlacement(
            instance_id=page.uid,
            source_page_id=page.uid,
        )
        for page in page_references
    ]


def render_organizer_thumbnails(
    documents: list[StoredPdf],
    visible_pages: list[PageReference],
) -> dict[str, RenderedThumbnail]:
    pages_by_document: dict[int, list[PageReference]] = {}
    for page in visible_pages:
        pages_by_document.setdefault(page.document_index, []).append(page)

    thumbnails_by_uid: dict[str, RenderedThumbnail] = {}
    for document_index, pages in pages_by_document.items():
        pages.sort(key=lambda page: page.page_index)
        page_numbers = tuple(page.page_index for page in pages)
        thumbnails = render_page_thumbnails(
            documents[document_index].content_hash,
            str(documents[document_index].path),
            page_numbers,
        )
        for page, thumbnail in zip(pages, thumbnails):
            thumbnails_by_uid[page.uid] = thumbnail

    return thumbnails_by_uid


def merge_pages_in_order(
    documents: list[StoredPdf],
    page_placements: list[PagePlacement],
) -> bytes:
    if not page_placements:
        raise ValueError("Keep at least one page in the organizer.")

    output_document = pymupdf.open()
    opened_documents: dict[int, pymupdf.Document] = {}
    try:
        for page_placement in page_placements:
            document_index, page_index = map(
                int,
                page_placement.source_page_id.split(":"),
            )
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
                (output_page.rotation + page_placement.rotation) % 360
            )
        output_bytes = output_document.tobytes()
    finally:
        output_document.close()
        for opened_document in opened_documents.values():
            opened_document.close()

    validate_pdf(output_bytes)
    return output_bytes
