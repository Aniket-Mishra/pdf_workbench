import atexit
import shutil
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class StoredPdf:
    document_id: str
    content_hash: str
    display_name: str
    path: Path
    page_count: int


def create_workspace_directory() -> Path:
    workspace_directory = Path(tempfile.mkdtemp(prefix="pdf-workbench-"))
    atexit.register(shutil.rmtree, workspace_directory, ignore_errors=True)
    return workspace_directory


def store_uploaded_pdfs(
    workspace_directory: Path,
    uploaded_files: list[tuple[str, bytes]],
    source_name: str,
) -> list[StoredPdf]:
    pending_uploads: list[tuple[StoredPdf, bytes]] = []
    content_occurrences: dict[str, int] = {}

    for display_name, pdf_bytes in uploaded_files:
        page_count = read_pdf_page_count(pdf_bytes, display_name)
        content_hash = sha256(pdf_bytes).hexdigest()
        occurrence = content_occurrences.get(content_hash, 0)
        content_occurrences[content_hash] = occurrence + 1

        pdf_path = workspace_directory / f"{content_hash}.pdf"
        pending_uploads.append(
            (
                StoredPdf(
                    document_id=f"{source_name}:{content_hash}:{occurrence}",
                    content_hash=content_hash,
                    display_name=display_name,
                    path=pdf_path,
                    page_count=page_count,
                ),
                pdf_bytes,
            )
        )

    for stored_pdf, pdf_bytes in pending_uploads:
        if not stored_pdf.path.exists():
            stored_pdf.path.write_bytes(pdf_bytes)

    return [stored_pdf for stored_pdf, _pdf_bytes in pending_uploads]


def read_pdf_page_count(pdf_bytes: bytes, display_name: str) -> int:
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.needs_pass:
                raise ValueError(
                    f"{display_name} is password-protected. Unlock it first."
                )
            page_count = document.page_count
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"Could not open {display_name} as a PDF.") from error

    if page_count < 1:
        raise ValueError(f"{display_name} has no pages.")
    return page_count


def remove_unlisted_pdfs(
    workspace_directory: Path,
    stored_pdfs: list[StoredPdf],
) -> None:
    active_paths = {stored_pdf.path for stored_pdf in stored_pdfs}
    for pdf_path in workspace_directory.glob("*.pdf"):
        if pdf_path not in active_paths:
            pdf_path.unlink()


def create_source_manifest(stored_pdfs: list[StoredPdf]) -> tuple[str, ...]:
    return tuple(stored_pdf.document_id for stored_pdf in stored_pdfs)
