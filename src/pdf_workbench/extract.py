import io
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
import pdfplumber
import pymupdf

from src.pdf_workbench.utils import (
    encode_numpy_array,
    encode_text,
    extract_formulas,
    sanitize_filename,
)


def build_extraction_zip(
    pdf_items: list[tuple[str, Path]],
) -> bytes:
    archive_buffer = io.BytesIO()
    paper_name_counts: dict[str, int] = {}

    with zipfile.ZipFile(
        archive_buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for display_name, pdf_path in pdf_items:
            paper_name = create_unique_paper_name(
                display_name,
                paper_name_counts,
            )
            write_pdf_to_archive(archive, pdf_path, paper_name)

    return archive_buffer.getvalue()


def create_unique_paper_name(
    display_name: str,
    paper_name_counts: dict[str, int],
) -> str:
    base_name = sanitize_filename(Path(display_name).stem)
    occurrence = paper_name_counts.get(base_name, 0) + 1
    paper_name_counts[base_name] = occurrence
    if occurrence == 1:
        return base_name
    return f"{base_name}_{occurrence}"


def write_pdf_to_archive(
    archive: zipfile.ZipFile,
    pdf_path: Path,
    paper_name: str,
) -> None:
    page_texts = write_page_content(archive, pdf_path, paper_name)
    write_table_content(archive, pdf_path, paper_name)
    write_combined_text(archive, paper_name, page_texts)


def write_page_content(
    archive: zipfile.ZipFile,
    pdf_path: Path,
    paper_name: str,
) -> list[str]:
    archive_root = PurePosixPath(paper_name)
    page_texts: list[str] = []

    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            page_text = page.get_text()
            page_texts.append(page_text)

            text_name = (
                archive_root
                / "text"
                / f"{paper_name}_page_{page_number}.txt"
            )
            markdown_name = text_name.with_suffix(".md")
            archive.writestr(text_name.as_posix(), encode_text(page_text))
            archive.writestr(
                markdown_name.as_posix(),
                encode_text(f"# Page {page_number}\n\n{page_text}"),
            )

            write_formula_content(
                archive,
                archive_root,
                paper_name,
                page_number,
                page_text,
            )
            write_image_content(
                archive,
                document,
                page,
                archive_root,
                paper_name,
                page_number,
            )

    return page_texts


def write_formula_content(
    archive: zipfile.ZipFile,
    archive_root: PurePosixPath,
    paper_name: str,
    page_number: int,
    page_text: str,
) -> None:
    formulas = extract_formulas(page_text)
    if not formulas:
        return

    formula_name = (
        archive_root
        / "formulas"
        / f"{paper_name}_page_{page_number}_formulas.md"
    )
    formula_text = "# Formulas\n\n" + "\n\n".join(
        f"$$\n{formula}\n$$" for formula in formulas
    )
    archive.writestr(formula_name.as_posix(), encode_text(formula_text))


def write_image_content(
    archive: zipfile.ZipFile,
    document: pymupdf.Document,
    page: pymupdf.Page,
    archive_root: PurePosixPath,
    paper_name: str,
    page_number: int,
) -> None:
    for image_index, image_details in enumerate(page.get_images(full=True), 1):
        image_reference = image_details[0]
        extracted_image = document.extract_image(image_reference)
        image_bytes = extracted_image["image"]
        image_extension = extracted_image.get("ext", "png")
        image_stem = f"{paper_name}_page_{page_number}_img_{image_index}"
        image_name = archive_root / "images" / (
            f"{image_stem}.{image_extension}"
        )
        array_name = archive_root / "images" / f"{image_stem}.npy"

        archive.writestr(image_name.as_posix(), image_bytes)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        archive.writestr(
            array_name.as_posix(),
            encode_numpy_array(image_array),
        )


def write_table_content(
    archive: zipfile.ZipFile,
    pdf_path: Path,
    paper_name: str,
) -> None:
    archive_root = PurePosixPath(paper_name)
    with pdfplumber.open(pdf_path) as document:
        for page_index, page in enumerate(document.pages):
            for table_index, table in enumerate(page.extract_tables(), 1):
                table_name = (
                    f"{paper_name}_page_{page_index + 1}"
                    f"_table_{table_index}"
                )
                table_frame = pd.DataFrame(table)
                csv_name = archive_root / "tables" / f"{table_name}.csv"
                markdown_name = (
                    archive_root / "tables" / f"{table_name}.md"
                )
                archive.writestr(
                    csv_name.as_posix(),
                    table_frame.to_csv(index=False, header=False),
                )
                archive.writestr(
                    markdown_name.as_posix(),
                    create_table_markdown(table_frame, table),
                )


def create_table_markdown(
    table_frame: pd.DataFrame,
    table: list[list[str | None]],
) -> str:
    try:
        return table_frame.to_markdown(index=False)
    except (ImportError, TypeError, ValueError):
        return "\n".join(
            " | ".join(str(value) for value in row)
            for row in table
        )


def write_combined_text(
    archive: zipfile.ZipFile,
    paper_name: str,
    page_texts: list[str],
) -> None:
    archive_root = PurePosixPath(paper_name)
    combined_text = "\n\n".join(page_texts)
    text_name = (
        archive_root
        / "combined_text"
        / f"{paper_name}_combined_all_text.txt"
    )
    markdown_name = text_name.with_suffix(".md")
    archive.writestr(text_name.as_posix(), encode_text(combined_text))
    archive.writestr(
        markdown_name.as_posix(),
        encode_text(f"# {paper_name} Combined Text\n\n{combined_text}"),
    )
