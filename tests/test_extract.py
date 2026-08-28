import io
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pymupdf

from src.pdf_workbench.extract import build_extraction_zip


def create_pdf_file(pdf_path: Path) -> None:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.insert_text((72, 72), "Total = 4")
        document.save(pdf_path)
    finally:
        document.close()


def create_pdf_with_image(pdf_path: Path) -> None:
    document = pymupdf.open()
    try:
        page = document.new_page()
        pixmap = pymupdf.Pixmap(
            pymupdf.csRGB,
            pymupdf.IRect(0, 0, 3, 2),
            False,
        )
        pixmap.clear_with(128)
        page.insert_image(
            pymupdf.Rect(0, 0, 30, 20),
            stream=pixmap.tobytes("png"),
        )
        document.save(pdf_path)
    finally:
        document.close()


def test_extraction_writes_text_and_formulas() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "paper.pdf"
        create_pdf_file(pdf_path)
        archive_bytes = build_extraction_zip([("paper.pdf", pdf_path)])

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert archive.read("paper/text/paper_page_1.txt").strip() == (
            b"Total = 4"
        )
        assert "paper/formulas/paper_page_1_formulas.md" in archive.namelist()
        assert archive.read(
            "paper/combined_text/paper_combined_all_text.txt"
        ).strip() == b"Total = 4"


def test_extraction_uses_distinct_folders_for_duplicate_names() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "paper.pdf"
        create_pdf_file(pdf_path)
        archive_bytes = build_extraction_zip(
            [("paper.pdf", pdf_path), ("paper.pdf", pdf_path)]
        )

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        archive_names = archive.namelist()

    assert len(archive_names) == len(set(archive_names))
    assert any(name.startswith("paper/") for name in archive_names)
    assert any(name.startswith("paper_2/") for name in archive_names)


def test_extraction_writes_decoded_image_arrays() -> None:
    with TemporaryDirectory() as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "images.pdf"
        create_pdf_with_image(pdf_path)
        archive_bytes = build_extraction_zip([("images.pdf", pdf_path)])

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        array_bytes = archive.read(
            "images/images/images_page_1_img_1.npy"
        )
        image_array = np.load(io.BytesIO(array_bytes))

    assert image_array.shape == (2, 3, 3)
    assert image_array.dtype == np.uint8
