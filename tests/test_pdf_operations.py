import io
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pikepdf
import pymupdf
import pytest

from src.pdf_workbench.basic_ops import (
    export_selected_pages,
    find_contiguous_page_ranges,
    merge_selected,
    validate_pdf,
)
from src.pdf_workbench.organizer import merge_pages_in_order
from src.pdf_workbench.page_grid import GridPage
from src.pdf_workbench.page_images import (
    RENDER_BATCH_SIZE,
    THUMBNAIL_WIDTH,
    RenderedPage,
    render_pages,
)
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


def test_contiguous_page_ranges_preserve_order() -> None:
    assert find_contiguous_page_ranges([0, 1, 2, 5, 7, 8]) == [
        (0, 2),
        (5, 5),
        (7, 8),
    ]


def test_pdf_validation_rejects_invalid_bytes() -> None:
    with pytest.raises(
        ValueError,
        match="Generated PDF failed structural validation",
    ):
        validate_pdf(b"not a PDF")


def test_merge_selected_copies_requested_pages() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=5)
        output_bytes = merge_selected(
            [("source", pdf_path)],
            {"source": [0, 1, 4]},
        )

    assert read_page_texts(output_bytes) == ["Page 1", "Page 2", "Page 5"]


def test_export_selected_pages_copies_requested_pages() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=4)
        output_bytes = export_selected_pages(pdf_path, [1, 3])

    assert read_page_texts(output_bytes) == ["Page 2", "Page 4"]


def test_export_selected_pages_preserves_metadata() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=2, title="Example")
        output_bytes = export_selected_pages(pdf_path, [0])

    with pymupdf.open(stream=output_bytes, filetype="pdf") as document:
        assert document.metadata["title"] == "Example"


def test_thumbnail_rendering_uses_requested_pages_only() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=30)
        thumbnails = render_pages(
            sha256(pdf_path.read_bytes()).hexdigest(),
            str(pdf_path),
            (10, 11, 12),
            THUMBNAIL_WIDTH,
        )

    assert [thumbnail.page_index for thumbnail in thumbnails] == [10, 11, 12]
    assert all(
        thumbnail.image_url.startswith("data:image/")
        for thumbnail in thumbnails
    )


def test_thumbnail_rendering_returns_every_page_in_bounded_batches(
    monkeypatch,
) -> None:
    rendered_page_batches: list[tuple[int, ...]] = []

    def render_page_batch(
        content_hash: str,
        pdf_path: str,
        page_numbers: tuple[int, ...],
        image_width: int,
    ) -> list[RenderedPage]:
        rendered_page_batches.append(page_numbers)
        return [
            RenderedPage(page_number, "data:image/png;base64,", 612, 792)
            for page_number in page_numbers
        ]

    monkeypatch.setattr(
        "src.pdf_workbench.page_images.render_page_batch",
        render_page_batch,
    )
    page_count = RENDER_BATCH_SIZE * 2 + 5
    page_numbers = tuple(range(page_count))

    thumbnails = render_pages(
        "source",
        "source.pdf",
        page_numbers,
        THUMBNAIL_WIDTH,
    )

    assert [len(batch) for batch in rendered_page_batches] == [
        RENDER_BATCH_SIZE,
        RENDER_BATCH_SIZE,
        5,
    ]
    assert len(thumbnails) == page_count


def test_organizer_merge_uses_thumbnail_order() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=3)
        document = StoredPdf(
            document_id="test:source:0",
            content_hash="source",
            display_name="source.pdf",
            path=pdf_path,
            page_count=3,
        )
        output_bytes = merge_pages_in_order(
            [document],
            [
                GridPage("third", "0:2"),
                GridPage("first", "0:0"),
                GridPage("second", "0:1"),
            ],
        )

    assert read_page_texts(output_bytes) == ["Page 3", "Page 1", "Page 2"]


def test_organizer_merge_duplicates_and_rotates_pages() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=2)
        document = StoredPdf(
            document_id="test:source:0",
            content_hash="source",
            display_name="source.pdf",
            path=pdf_path,
            page_count=2,
        )
        output_bytes = merge_pages_in_order(
            [document],
            [
                GridPage("first", "0:0", rotation=90),
                GridPage("first-copy", "0:0", rotation=180),
                GridPage("second", "0:1"),
            ],
        )

    with pymupdf.open(stream=output_bytes, filetype="pdf") as output_document:
        page_texts = [page.get_text().strip() for page in output_document]
        page_rotations = [page.rotation for page in output_document]

    assert page_texts == ["Page 1", "Page 1", "Page 2"]
    assert page_rotations == [90, 180, 0]


def test_organizer_merge_accepts_recoverable_pdf_warnings() -> None:
    source_stream = io.BytesIO()
    with pikepdf.Pdf.new() as source_document:
        page = source_document.add_blank_page()
        page.Contents = pikepdf.Stream(source_document, b"q\nQ\n")
        source_document.save(
            source_stream,
            compress_streams=False,
            object_stream_mode=pikepdf.ObjectStreamMode.disable,
        )

    source_bytes = source_stream.getvalue().replace(
        b"/Length 4",
        b"/Length 6",
        1,
    )
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "recoverable.pdf"
        pdf_path.write_bytes(source_bytes)
        document = StoredPdf(
            document_id="test:recoverable:0",
            content_hash="recoverable",
            display_name="recoverable.pdf",
            path=pdf_path,
            page_count=1,
        )
        output_bytes = merge_pages_in_order(
            [document],
            [GridPage("first", "0:0")],
        )

    with pikepdf.Pdf.open(
        io.BytesIO(output_bytes),
        attempt_recovery=False,
    ) as output_document:
        assert len(output_document.pages) == 1
