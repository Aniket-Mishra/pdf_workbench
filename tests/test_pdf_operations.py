from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from src.pdf_workbench.basic_ops import (
    filter_selected_per_file,
    find_contiguous_page_ranges,
    merge_selected,
)
from src.pdf_workbench.organizer import (
    PagePlacement,
    merge_pages_in_order,
)
from src.pdf_workbench.thumbnails import (
    RenderedThumbnail,
    THUMBNAIL_BATCH_SIZE,
    render_page_thumbnails,
)
from src.pdf_workbench.workspace import StoredPdf


def create_pdf_file(pdf_path: Path, page_count: int) -> None:
    document = pymupdf.open()
    try:
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


def test_merge_selected_copies_requested_pages() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=5)
        output_bytes = merge_selected(
            [("source", pdf_path)],
            {"source": [0, 1, 4]},
        )

    assert read_page_texts(output_bytes) == ["Page 1", "Page 2", "Page 5"]


def test_filter_selected_copies_requested_pages() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=4)
        output_bytes = filter_selected_per_file(pdf_path, [1, 3])

    assert read_page_texts(output_bytes) == ["Page 2", "Page 4"]


def test_thumbnail_rendering_uses_requested_pages_only() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "source.pdf"
        create_pdf_file(pdf_path, page_count=30)
        thumbnails = render_page_thumbnails(
            sha256(pdf_path.read_bytes()).hexdigest(),
            str(pdf_path),
            (10, 11, 12),
        )

    assert len(thumbnails) == 3
    assert all(
        thumbnail.mime_type in {"image/jpeg", "image/png"}
        for thumbnail in thumbnails
    )
    assert all(thumbnail.image_bytes for thumbnail in thumbnails)


def test_thumbnail_rendering_returns_every_page_in_bounded_batches(
    monkeypatch,
) -> None:
    rendered_page_batches: list[tuple[int, ...]] = []

    def render_thumbnail_batch(
        content_hash: str,
        pdf_path: str,
        page_numbers: tuple[int, ...],
        thumbnail_width: int,
    ) -> list[RenderedThumbnail]:
        rendered_page_batches.append(page_numbers)
        return [
            RenderedThumbnail(b"thumbnail", "image/png")
            for _ in page_numbers
        ]

    monkeypatch.setattr(
        "src.pdf_workbench.thumbnails.render_thumbnail_batch",
        render_thumbnail_batch,
    )
    page_count = 100
    page_numbers = tuple(range(page_count))

    thumbnails = render_page_thumbnails(
        "source",
        "source.pdf",
        page_numbers,
    )

    assert [len(batch) for batch in rendered_page_batches] == [
        THUMBNAIL_BATCH_SIZE,
        THUMBNAIL_BATCH_SIZE,
        page_count - THUMBNAIL_BATCH_SIZE * 2,
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
                PagePlacement("third", "0:2"),
                PagePlacement("first", "0:0"),
                PagePlacement("second", "0:1"),
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
                PagePlacement("first", "0:0", rotation=90),
                PagePlacement("first-copy", "0:0", rotation=180),
                PagePlacement("second", "0:1"),
            ],
        )

    with pymupdf.open(stream=output_bytes, filetype="pdf") as output_document:
        page_texts = [page.get_text().strip() for page in output_document]
        page_rotations = [page.rotation for page in output_document]

    assert page_texts == ["Page 1", "Page 1", "Page 2"]
    assert page_rotations == [90, 180, 0]
