import io
import zipfile
from pathlib import Path

import streamlit as st

from src.pdf_workbench.basic_ops import (
    filter_selected_per_file,
    merge_selected,
)
from src.pdf_workbench.extract import build_extraction_zip
from src.pdf_workbench.page_selector import select_pdf_pages


st.title("Workbench")
st.caption("Select pages, merge PDFs, filter pages, or extract contents.")

stored_pdfs = list(st.session_state.get("workbench_docs", []))
if not stored_pdfs:
    st.info("Open PDFs in the viewer first.")
    st.stop()

st.subheader("Select pages")
st.caption("Click pages to limit the output. No selection uses every page.")

selections: dict[str, list[int]] = {}
for stored_pdf in stored_pdfs:
    expander_label = (
        f"{stored_pdf.display_name} ({stored_pdf.page_count} pages)"
    )
    with st.expander(expander_label, expanded=len(stored_pdfs) <= 2):
        selections[stored_pdf.document_id] = select_pdf_pages(
            pdf_path=stored_pdf.path,
            content_hash=stored_pdf.content_hash,
            document_id=stored_pdf.document_id,
            page_count=stored_pdf.page_count,
        )

selected_page_count = sum(
    len(selected_pages) for selected_pages in selections.values()
)
st.caption(f"{selected_page_count} pages selected")

merge_column, filter_column, extract_column = st.columns(3)
with merge_column:
    merge_pdf = st.button(
        "Merge PDFs",
        type="primary",
        use_container_width=True,
    )
with filter_column:
    filter_pdfs = st.button("Filter PDFs", use_container_width=True)
with extract_column:
    extract_contents = st.button(
        "Extract contents",
        use_container_width=True,
    )

if merge_pdf:
    merged_pdf = merge_selected(
        [
            (stored_pdf.document_id, stored_pdf.path)
            for stored_pdf in stored_pdfs
        ],
        selections,
    )
    st.download_button(
        "Download merged.pdf",
        data=merged_pdf,
        file_name="merged.pdf",
        mime="application/pdf",
    )

if filter_pdfs:
    filtered_files = [
        (
            stored_pdf.display_name,
            filter_selected_per_file(
                stored_pdf.path,
                selections.get(stored_pdf.document_id, []),
            ),
        )
        for stored_pdf in stored_pdfs
    ]

    if len(filtered_files) == 1:
        display_name, filtered_pdf = filtered_files[0]
        download_name = f"{Path(display_name).stem}_filtered.pdf"
        st.download_button(
            f"Download {download_name}",
            data=filtered_pdf,
            file_name=download_name,
            mime="application/pdf",
        )
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(
            zip_buffer,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zip_file:
            for file_number, (display_name, filtered_pdf) in enumerate(
                filtered_files,
                1,
            ):
                download_name = (
                    f"{Path(display_name).stem}_{file_number}_filtered.pdf"
                )
                zip_file.writestr(download_name, filtered_pdf)

        st.download_button(
            "Download filtered_pdfs.zip",
            data=zip_buffer.getvalue(),
            file_name="filtered_pdfs.zip",
            mime="application/zip",
        )

if extract_contents:
    with st.spinner("Extracting contents..."):
        extraction_zip = build_extraction_zip(
            [
                (stored_pdf.display_name, stored_pdf.path.read_bytes())
                for stored_pdf in stored_pdfs
            ]
        )
    st.download_button(
        "Download extracted_contents.zip",
        data=extraction_zip,
        file_name="extracted_contents.zip",
        mime="application/zip",
    )
