from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from src.pdf_workbench.workspace import (
    create_source_manifest,
    remove_unlisted_pdfs,
    store_uploaded_pdfs,
)


def create_pdf_bytes(text: str) -> bytes:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


def test_same_filename_with_different_content_gets_distinct_identity() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        stored_pdfs = store_uploaded_pdfs(
            Path(temporary_directory_name),
            [
                ("paper.pdf", create_pdf_bytes("first")),
                ("paper.pdf", create_pdf_bytes("second")),
            ],
            source_name="test",
        )

    assert stored_pdfs[0].document_id != stored_pdfs[1].document_id
    assert stored_pdfs[0].path != stored_pdfs[1].path


def test_duplicate_content_shares_file_and_keeps_distinct_identity() -> None:
    pdf_bytes = create_pdf_bytes("same")

    with TemporaryDirectory() as temporary_directory_name:
        stored_pdfs = store_uploaded_pdfs(
            Path(temporary_directory_name),
            [("paper.pdf", pdf_bytes), ("copy.pdf", pdf_bytes)],
            source_name="test",
        )

    assert stored_pdfs[0].document_id != stored_pdfs[1].document_id
    assert stored_pdfs[0].path == stored_pdfs[1].path


def test_source_manifest_changes_with_uploaded_documents() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        workspace_directory = Path(temporary_directory_name)
        first_pdf = store_uploaded_pdfs(
            workspace_directory,
            [("first.pdf", create_pdf_bytes("first"))],
            source_name="test",
        )
        second_pdf = store_uploaded_pdfs(
            workspace_directory,
            [("second.pdf", create_pdf_bytes("second"))],
            source_name="test",
        )

    assert create_source_manifest(first_pdf) != create_source_manifest(
        second_pdf
    )


def test_remove_unlisted_pdfs_deletes_old_uploads() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        workspace_directory = Path(temporary_directory_name)
        first_pdf = store_uploaded_pdfs(
            workspace_directory,
            [("first.pdf", create_pdf_bytes("first"))],
            source_name="test",
        )[0]
        second_pdfs = store_uploaded_pdfs(
            workspace_directory,
            [("second.pdf", create_pdf_bytes("second"))],
            source_name="test",
        )

        remove_unlisted_pdfs(workspace_directory, second_pdfs)

        assert not first_pdf.path.exists()
        assert second_pdfs[0].path.exists()
