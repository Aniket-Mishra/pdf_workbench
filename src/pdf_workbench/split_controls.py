import io
import zipfile
from pathlib import Path

import streamlit as st

from src.pdf_workbench.split import (
    create_single_page_groups,
    group_pages_by_count,
    iter_split_pdf_parts,
    parse_split_ranges,
)
from src.pdf_workbench.workspace import StoredPdf


def show_split_controls(
    stored_pdfs: list[StoredPdf],
    selections: dict[str, list[int]],
) -> None:
    split_mode = st.selectbox(
        "Split mode",
        ("Ranges", "Every N pages", "Selected pages"),
    )

    split_ranges = ""
    pages_per_file = 10
    if split_mode == "Ranges":
        split_ranges = st.text_input(
            "Ranges",
            placeholder="1-5, 6-10, 11-end",
            help="Each comma-separated range becomes one PDF.",
        )
    elif split_mode == "Every N pages":
        pages_per_file = int(
            st.number_input(
                "Pages per file",
                min_value=1,
                value=10,
                step=1,
            )
        )
    else:
        st.caption("Each selected page becomes a separate PDF.")

    if not st.button("Split PDFs", use_container_width=True):
        return

    try:
        with st.spinner("Splitting PDFs..."):
            output_name, output_bytes, output_mime_type = (
                build_split_download(
                    stored_pdfs,
                    selections,
                    split_mode,
                    split_ranges,
                    pages_per_file,
                )
            )
    except ValueError as error:
        st.error(str(error))
        return

    st.download_button(
        f"Download {output_name}",
        data=output_bytes,
        file_name=output_name,
        mime=output_mime_type,
        on_click="ignore",
    )


def build_split_download(
    stored_pdfs: list[StoredPdf],
    selections: dict[str, list[int]],
    split_mode: str,
    split_ranges: str,
    pages_per_file: int,
) -> tuple[str, bytes, str]:
    split_plan: list[tuple[int, StoredPdf, list[list[int]]]] = []
    for document_number, stored_pdf in enumerate(stored_pdfs, 1):
        if split_mode == "Ranges":
            page_groups = parse_split_ranges(
                split_ranges,
                stored_pdf.page_count,
            )
        elif split_mode == "Every N pages":
            page_groups = group_pages_by_count(
                stored_pdf.page_count,
                pages_per_file,
            )
        elif split_mode == "Selected pages":
            selected_pages = selections.get(stored_pdf.document_id, [])
            if not selected_pages:
                continue
            page_groups = create_single_page_groups(selected_pages)
        else:
            raise ValueError(f"Unknown split mode: {split_mode}.")

        split_plan.append((document_number, stored_pdf, page_groups))

    if not split_plan:
        raise ValueError("Select at least one page before splitting.")

    output_count = sum(len(page_groups) for _, _, page_groups in split_plan)
    if output_count == 1:
        document_number, stored_pdf, page_groups = split_plan[0]
        output_name = create_split_name(
            stored_pdf,
            document_number,
            len(stored_pdfs),
            part_number=1,
        )
        output_bytes, = iter_split_pdf_parts(stored_pdf.path, page_groups)
        return output_name, output_bytes, "application/pdf"

    split_archive = io.BytesIO()
    with zipfile.ZipFile(
        split_archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zip_file:
        for document_number, stored_pdf, page_groups in split_plan:
            for part_number, output_bytes in enumerate(
                iter_split_pdf_parts(stored_pdf.path, page_groups),
                1,
            ):
                output_name = create_split_name(
                    stored_pdf,
                    document_number,
                    len(stored_pdfs),
                    part_number,
                )
                zip_file.writestr(output_name, output_bytes)

    return "split_pdfs.zip", split_archive.getvalue(), "application/zip"


def create_split_name(
    stored_pdf: StoredPdf,
    document_number: int,
    document_count: int,
    part_number: int,
) -> str:
    document_prefix = Path(stored_pdf.display_name).stem
    if document_count > 1:
        document_prefix = f"{document_number}_{document_prefix}"
    return f"{document_prefix}_part_{part_number:03}.pdf"
